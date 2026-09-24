#ifndef FLIP_OTA_SIGSTORE_VERIFY_H_
#define FLIP_OTA_SIGSTORE_VERIFY_H_

#include <zephyr/kernel.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

int sigstore_verify_init(void);
bool sigstore_verify_image_signature(const uint8_t *image_sha256,
                                     const uint8_t *signature_r_s,
                                     const uint8_t *public_key_raw);

#ifdef __cplusplus
}
#endif

#endif /* FLIP_OTA_SIGSTORE_VERIFY_H_ */
