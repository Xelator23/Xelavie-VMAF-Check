/* MIT, Xelavie VMAF Check. Bounded 16-bit YUV420 input: legacy interleaved
 * pairs or compact 25% samples. Colour metadata is explicit, never inferred. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <libvmaf/libvmaf.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static int picture(VmafContext *ctx, VmafPicture *pic, int known) {
    if (vmaf_fetch_preallocated_picture(ctx, pic)) return -1;
    if (known) pic->color = (VmafColor){VMAF_COLOR_RANGE_LIMITED,
        VMAF_COLOR_PRIMARIES_BT2020, VMAF_COLOR_TRC_SMPTE2084,
        VMAF_COLOR_MATRIX_BT2020_NCL};
    else pic->color = (VmafColor){0};
    for (int p=0; p<3; p++) for (unsigned y=0; y<pic->h[p]; y++) {
        size_t size=pic->w[p]*2;
        if (fread((uint8_t *)pic->data[p]+y*pic->stride[p],1,size,stdin)!=size) {
            vmaf_picture_unref(pic);
            fprintf(stderr,"Truncated frame pair\n"); return -1;
        }
    }
    return 0;
}

static int legacy_main(int argc, char **argv) {
    if (argc==2 && !strcmp(argv[1],"--version")) {
        printf("xelavie-hdr-worker protocol=2 libvmaf=%s zimg=required sparse25=1\n",vmaf_version()); return 0;
    }
    if (argc!=8) {fprintf(stderr,"Usage: worker width height threads step model.json output.json pq|unknown\n");return 2;}
    unsigned w=(unsigned)atoi(argv[1]),h=(unsigned)atoi(argv[2]);
    unsigned threads=(unsigned)atoi(argv[3]),step=(unsigned)atoi(argv[4]);
    if (!w || !h || w>16384 || h>16384 || (w%2) || (h%2) || threads>64 || !step || step>4 ||
        (strcmp(argv[7],"pq") && strcmp(argv[7],"unknown"))) return 2;
#ifdef _WIN32
    _setmode(_fileno(stdin),_O_BINARY);
#endif
    setvbuf(stdout,NULL,_IOLBF,0);
    VmafContext *ctx=NULL; VmafModel *model=NULL; int err=1;
    VmafConfiguration cfg={.log_level=VMAF_LOG_LEVEL_ERROR,.n_threads=threads,
        .n_subsample=step,.gpumask=UINT64_MAX};
    VmafModelConfig mc={.name="vmaf"};
    if (vmaf_init(&ctx,cfg)) goto done;
    if (vmaf_model_load_from_path(&model,&mc,argv[5])) goto done;
    if (vmaf_use_features_from_model(ctx,model)) goto done;
    VmafPictureConfiguration pool={.pic_params={.w=w,.h=h,.bpc=16,.pix_fmt=VMAF_PIX_FMT_YUV420P},
        .pic_cnt=2*((threads?threads:1)+2)};
    if (vmaf_preallocate_pictures(ctx,pool)) goto done;
    unsigned count=0;
    for (;;) {
        int next=fgetc(stdin);
        if (next==EOF) {if (ferror(stdin)) goto done; break;}
        ungetc(next,stdin);
        VmafPicture ref={0},dist={0};
        if (picture(ctx,&ref,!strcmp(argv[7],"pq"))) goto done;
        if (picture(ctx,&dist,!strcmp(argv[7],"pq"))) {vmaf_picture_unref(&ref);goto done;}
        if (vmaf_read_pictures(ctx,&ref,&dist,count++)) goto done;
        printf("frame=%u\n",count);fflush(stdout);
    }
    if (!count || vmaf_read_pictures(ctx,NULL,NULL,0)) goto done;
    double score;
    if (vmaf_score_pooled(ctx,model,VMAF_POOL_METHOD_MEAN,&score,0,count-1)) goto done;
    if (vmaf_write_output(ctx,argv[6],VMAF_OUTPUT_FORMAT_JSON)) goto done;
    err=0;
done:
    /* On a failed read, libvmaf may retain a borrowed pool picture. Closing that
     * failed pool waits forever. End this isolated worker process on errors;
     * the OS reclaims its resources (same error strategy as the upstream CLI). */
    if (err) {fprintf(stderr,"HDR worker failed: colour conversion, model or input invalid\n");return err;}
    if (model) vmaf_model_destroy(model);
    if (ctx) vmaf_close(ctx);
    return err;
}

/* Compact protocol; same pinned conversion and original frame indices. */
#include <errno.h>
#include <limits.h>
#include "conversion_policy.h"
#include "model.h"
#include "picture.h"

static int converted(VmafContext *ctx,VmafPicture *dest,VmafModel *model,
                     VmafPictureConvertContext **converter){
 VmafPicture raw={0};
 if(picture(ctx,&raw,1))return -1;
 VmafPictureConvertTarget requested={.pix_fmt=model->conversion_target.pix_fmt,
  .bpc=model->conversion_target.bpc,.color=model->conversion_target.color};
 VmafPictureConvertTarget target={0},other={0};bool needed=false;
 if(vmaf_conversion_policy_target(&raw,&raw,&requested,&needed,&target))return -1;
 other=target;
 if(model->conversion_target.display_resolution&&vmaf_conversion_policy_scale(
  &raw,&raw,model->conversion_target.display_resolution,&needed,&target,&other))return -1;
 if(vmaf_conversion_policy_picture_matches(&raw,&target)){*dest=raw;return 0;}
 if(!*converter&&vmaf_picture_convert_context_init(converter,&raw,&target))return -1;
 int error=vmaf_picture_convert(*converter,dest,&raw);
 vmaf_picture_unref(&raw);return error;
}
int main(int argc,char **argv){
 /* Like the legacy path, errors end this isolated process without waiting
  * on a failed picture pool. The parent reaps all decoder/worker processes. */
 if(argc!=9)return legacy_main(argc,argv);
 if(strcmp(argv[7],"pq-sparse25"))return 2;
 unsigned w=atoi(argv[1]),h=atoi(argv[2]),threads=atoi(argv[3]),step=atoi(argv[4]);
 char *end=NULL;errno=0;unsigned long total=strtoul(argv[8],&end,10);
 if(errno||!*argv[8]||*end||!total||total>UINT_MAX||*argv[8]=='-'||step!=4||
    !w||!h||w>16384||h>16384||w%2||h%2||threads>64)return 2;
#ifdef _WIN32
 _setmode(_fileno(stdin),_O_BINARY);
#endif
 setvbuf(stdout,NULL,_IOLBF,0);
 VmafContext *ctx=NULL;VmafModel *model=NULL;VmafPicture last={0};
 VmafPictureConvertContext *convert[2]={NULL,NULL};
 VmafConfiguration cfg={.log_level=VMAF_LOG_LEVEL_ERROR,.n_threads=threads,
  .n_subsample=step,.gpumask=UINT64_MAX};VmafModelConfig mc={.name="vmaf"};
 if(vmaf_init(&ctx,cfg)||vmaf_model_load_from_path(&model,&mc,argv[5])||
    vmaf_use_features_from_model(ctx,model))return 3;
 if(!model->conversion_target.enabled||model->conversion_target.has_assumed_color)return 3;
 VmafPictureConfiguration pool={.pic_params={.w=w,.h=h,.bpc=16,.pix_fmt=VMAF_PIX_FMT_YUV420P},
  .pic_cnt=2*((threads?threads:1)+2)};
 if(vmaf_preallocate_pictures(ctx,pool))return 3;
 unsigned refs=0,encs=0;
 for(unsigned n=0;n<total;n++){
  VmafPicture ref={0},dist={0};
  if(n%4!=2){
   if(last.priv)vmaf_picture_unref(&last);
   if(converted(ctx,&last,model,&convert[0]))return 4;
   refs++;
  }
  if(vmaf_picture_ref(&ref,&last))return 4;
  if(n%4==0){if(converted(ctx,&dist,model,&convert[1]))return 4;encs++;}
  else if(vmaf_picture_ref(&dist,&last))return 4;
  if(vmaf_read_pictures(ctx,&ref,&dist,n))return 5;
  printf("frame=%u\n",n+1);fflush(stdout);
 }
 if(fgetc(stdin)!=EOF||ferror(stdin))return 6;
 if(last.priv)vmaf_picture_unref(&last);
 double score;
 if(vmaf_read_pictures(ctx,NULL,NULL,0)||vmaf_score_pooled(ctx,model,VMAF_POOL_METHOD_MEAN,&score,0,total-1)||
    vmaf_write_output(ctx,argv[6],VMAF_OUTPUT_FORMAT_JSON))return 7;
 for(int i=0;i<2;i++)if(convert[i])vmaf_picture_convert_context_close(convert[i]);
 vmaf_model_destroy(model);vmaf_close(ctx);
 fprintf(stderr,"sparse25 frames=%lu reference_conversions=%u encoded_conversions=%u\n",total,refs,encs);
 return 0;
}
