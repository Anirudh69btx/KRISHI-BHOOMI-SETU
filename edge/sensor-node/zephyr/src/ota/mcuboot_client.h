#ifndef FLIP_OTA_MCUBOOT_CLIENT_H_
#define FLIP_OTA_MCUBOOT_CLIENT_H_

#include <zephyr/kernel.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int mcuboot_client_init(void);
bool mcuboot_client_is_confirmed(void);
int mcuboot_client_confirm_running_image(void);
int mcuboot_client_request_upgrade(bool permanent);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_OTA_MCUBOOT_CLIENT_H_ */
