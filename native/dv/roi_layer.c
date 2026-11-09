/* SPDX-License-Identifier: MIT
 * PRIVATE single-device experiment, explicitly enabled per child process.
 * No registration/driver replacement. Retains viewports, textures and shaders;
 * narrows only scissors on full-sized video planes, with a conservative halo.
 * Not a general-purpose or production Vulkan layer. */
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
static PFN_vkGetInstanceProcAddr next_gipa;
static PFN_GetPhysicalDeviceProcAddr next_gppa;
static PFN_vkGetDeviceProcAddr next_gdpa;
static PFN_vkCmdSetScissor next_scissor;
static PFN_vkDestroyInstance next_destroy_instance;
static VkInstance current_instance;
static VkDevice current_device;
static int fw,fh,cx,cy,cw,ch,halo,enabled;
static atomic_uint calls,changed;

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL roi_gipa(VkInstance,const char *);
static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL roi_gdpa(VkDevice,const char *);

static VKAPI_ATTR void VKAPI_CALL roi_scissor(VkCommandBuffer cmd,uint32_t first,
                                             uint32_t count,const VkRect2D *rects){
    VkRect2D local[16];
    atomic_fetch_add(&calls,1);
    if(!enabled || count>16){next_scissor(cmd,first,count,rects);return;}
    memcpy(local,rects,count*sizeof(*rects));
    for(uint32_t i=0;i<count;i++){
        VkRect2D *r=&local[i];
        int w=(int)r->extent.width,h=(int)r->extent.height;
        if(r->offset.x || r->offset.y || (w!=fw && 2*w!=fw) || (h!=fh && 2*h!=fh))continue;
        int x0=(int)((int64_t)cx*w/fw)-halo;
        int y0=(int)((int64_t)cy*h/fh)-halo;
        int x1=(int)(((int64_t)(cx+cw)*w+fw-1)/fw)+halo;
        int y1=(int)(((int64_t)(cy+ch)*h+fh-1)/fh)+halo;
        if(x0<0)x0=0;if(y0<0)y0=0;if(x1>w)x1=w;if(y1>h)y1=h;
        if(x1<=x0 || y1<=y0)continue;
        r->offset.x=x0;r->offset.y=y0;r->extent.width=x1-x0;r->extent.height=y1-y0;
        if(x0 || y0 || x1<w || y1<h)atomic_fetch_add(&changed,1);
    }
    next_scissor(cmd,first,count,local);
}

static VKAPI_ATTR void VKAPI_CALL roi_destroy_instance(VkInstance instance,const VkAllocationCallbacks *alloc){
    fprintf(stderr,"XELAVIE_ROI calls=%u narrowed=%u enabled=%d\n",atomic_load(&calls),atomic_load(&changed),enabled);
    next_destroy_instance(instance,alloc);
}

static VKAPI_ATTR VkResult VKAPI_CALL roi_create_instance(const VkInstanceCreateInfo *ci,
                                  const VkAllocationCallbacks *alloc,VkInstance *instance){
    VkLayerInstanceCreateInfo *link=(VkLayerInstanceCreateInfo *)ci->pNext;
    while(link && !(link->sType==VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO && link->function==VK_LAYER_LINK_INFO))
        link=(VkLayerInstanceCreateInfo *)link->pNext;
    if(!link || current_instance)return VK_ERROR_INITIALIZATION_FAILED;
    next_gipa=link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    next_gppa=link->u.pLayerInfo->pfnNextGetPhysicalDeviceProcAddr;
    PFN_vkCreateInstance create=(PFN_vkCreateInstance)next_gipa(VK_NULL_HANDLE,"vkCreateInstance");
    link->u.pLayerInfo=link->u.pLayerInfo->pNext;
    VkResult result=create(ci,alloc,instance);
    if(result==VK_SUCCESS){
        current_instance=*instance;
        next_destroy_instance=(PFN_vkDestroyInstance)next_gipa(*instance,"vkDestroyInstance");
        const char *value=getenv("XELAVIE_ROI");
        if(value && sscanf(value,"%d:%d:%d:%d:%d:%d:%d",&fw,&fh,&cx,&cy,&cw,&ch,&halo)==7 &&
           fw>0 && fh>0 && fw<=16384 && fh<=16384 && cx>=0 && cy>=0 && cw>0 && ch>0 &&
           cw<=fw-cx && ch<=fh-cy && halo>=0 && halo<=256)enabled=1;
        fprintf(stderr,"XELAVIE_ROI loaded enabled=%d region=%d:%d:%d:%d:%d:%d halo=%d\n",enabled,fw,fh,cx,cy,cw,ch,halo);
    }
    return result;
}

static VKAPI_ATTR VkResult VKAPI_CALL roi_create_device(VkPhysicalDevice physical,const VkDeviceCreateInfo *ci,
                                  const VkAllocationCallbacks *alloc,VkDevice *device){
    VkLayerDeviceCreateInfo *link=(VkLayerDeviceCreateInfo *)ci->pNext;
    while(link && !(link->sType==VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && link->function==VK_LAYER_LINK_INFO))
        link=(VkLayerDeviceCreateInfo *)link->pNext;
    if(!link || current_device)return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa=link->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    next_gdpa=link->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    PFN_vkCreateDevice create=(PFN_vkCreateDevice)gipa(current_instance,"vkCreateDevice");
    link->u.pLayerInfo=link->u.pLayerInfo->pNext;
    VkResult result=create(physical,ci,alloc,device);
    if(result==VK_SUCCESS){
        current_device=*device;
        next_scissor=(PFN_vkCmdSetScissor)next_gdpa(*device,"vkCmdSetScissor");
    }
    return result;
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL roi_gdpa(VkDevice device,const char *name){
    if(!strcmp(name,"vkGetDeviceProcAddr"))return (PFN_vkVoidFunction)roi_gdpa;
    if(!strcmp(name,"vkCmdSetScissor"))return (PFN_vkVoidFunction)roi_scissor;
    return next_gdpa?next_gdpa(device,name):NULL;
}
static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL roi_gipa(VkInstance instance,const char *name){
    if(!strcmp(name,"vkGetInstanceProcAddr"))return (PFN_vkVoidFunction)roi_gipa;
    if(!strcmp(name,"vkGetDeviceProcAddr"))return (PFN_vkVoidFunction)roi_gdpa;
    if(!strcmp(name,"vkCreateInstance"))return (PFN_vkVoidFunction)roi_create_instance;
    if(!strcmp(name,"vkCreateDevice"))return (PFN_vkVoidFunction)roi_create_device;
    if(!strcmp(name,"vkCmdSetScissor"))return (PFN_vkVoidFunction)roi_scissor;
    if(!strcmp(name,"vkDestroyInstance"))return (PFN_vkVoidFunction)roi_destroy_instance;
    return next_gipa?next_gipa(instance,name):NULL;
}
static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL roi_gppa(VkInstance instance,const char *name){
    return next_gppa?next_gppa(instance,name):NULL;
}
EXPORT VKAPI_ATTR VkResult VKAPI_CALL vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *info){
    if(info->loaderLayerInterfaceVersion<2)return VK_ERROR_INITIALIZATION_FAILED;
    info->loaderLayerInterfaceVersion=2;
    info->pfnGetInstanceProcAddr=roi_gipa;info->pfnGetDeviceProcAddr=roi_gdpa;
    info->pfnGetPhysicalDeviceProcAddr=roi_gppa;
    return VK_SUCCESS;
}
