#include "littlefs_manager.h"
#include <zephyr/fs/fs.h>
#include <zephyr/fs/littlefs.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include <string.h>

LOG_MODULE_REGISTER(littlefs_mgr, LOG_LEVEL_INF);

#define LFS_MOUNT_POINT "/lfs"
#define MAX_STORED_PACKETS 1200 // 90% capacity threshold for 448KB partition

FS_LITTLEFS_DECLARE_DEFAULT_CONFIG(cstorage);
static struct fs_mount_t lfs_mnt = {
    .type = FS_LITTLEFS,
    .fs_data = &cstorage,
    .storage_dev = (void *)FLASH_AREA_ID(storage_partition),
    .mnt_point = LFS_MOUNT_POINT,
};

static bool is_mounted = false;
static size_t buffered_count = 0;

/* Purge oldest packet when buffer reaches 90% capacity */
static void prune_oldest_if_needed(void)
{
    if (buffered_count < MAX_STORED_PACKETS) {
        return;
    }

    struct fs_dir_t dirp;
    fs_dir_t_init(&dirp);
    if (fs_opendir(&dirp, LFS_MOUNT_POINT) != 0) {
        return;
    }

    struct fs_dirent entry;
    char oldest_file[48] = "";

    while (fs_readdir(&dirp, &entry) == 0 && entry.name[0] != '\0') {
        if (entry.type == FS_DIR_ENTRY_FILE && strncmp(entry.name, "pkt_", 4) == 0) {
            if (oldest_file[0] == '\0' || strcmp(entry.name, oldest_file) < 0) {
                snprintf(oldest_file, sizeof(oldest_file), "%s", entry.name);
            }
        }
    }
    fs_closedir(&dirp);

    if (oldest_file[0] != '\0') {
        char full_path[56];
        snprintf(full_path, sizeof(full_path), "%s/%s", LFS_MOUNT_POINT, oldest_file);
        fs_unlink(full_path);
        if (buffered_count > 0) buffered_count--;
        LOG_WRN("Pruned oldest telemetry packet %s (buffer > 90%% capacity)", oldest_file);
    }
}

int littlefs_init(void)
{
    int ret = fs_mount(&lfs_mnt);
    if (ret != 0) {
        LOG_WRN("LittleFS mount failed (%d), formatting storage partition...", ret);
        ret = fs_mount(&lfs_mnt);
        if (ret != 0) {
            LOG_ERR("Fatal: Unable to mount LittleFS (%d)", ret);
            return ret;
        }
    }

    is_mounted = true;
    LOG_INF("LittleFS successfully mounted on %s", LFS_MOUNT_POINT);

    /* Enumerate existing files */
    struct fs_dir_t dirp;
    fs_dir_t_init(&dirp);
    ret = fs_opendir(&dirp, LFS_MOUNT_POINT);
    if (ret == 0) {
        struct fs_dirent entry;
        buffered_count = 0;
        while (fs_readdir(&dirp, &entry) == 0 && entry.name[0] != '\0') {
            if (entry.type == FS_DIR_ENTRY_FILE && strncmp(entry.name, "pkt_", 4) == 0) {
                buffered_count++;
            }
        }
        fs_closedir(&dirp);
    }
    LOG_INF("Discovered %zu buffered packets in LittleFS", buffered_count);
    return 0;
}

int littlefs_write_packet(const struct sensor_packet *pkt)
{
    if (!is_mounted || !pkt) {
        return -EINVAL;
    }

    prune_oldest_if_needed();

    char filename[40];
    snprintf(filename, sizeof(filename), "%s/pkt_%05u.bin", LFS_MOUNT_POINT, pkt->seq_id);

    struct fs_file_t file;
    fs_file_t_init(&file);

    int ret = fs_open(&file, filename, FS_O_CREATE | FS_O_WRITE);
    if (ret != 0) {
        LOG_ERR("Failed to open %s (%d)", filename, ret);
        return ret;
    }

    /* Transactional write: write data, fs_sync to flush to SPI NOR flash */
    ssize_t written = fs_write(&file, pkt, sizeof(*pkt));
    fs_sync(&file);
    fs_close(&file);

    if (written == sizeof(*pkt)) {
        buffered_count++;
        LOG_INF("Buffered seq=%u to flash (total=%zu)", pkt->seq_id, buffered_count);
        return 0;
    }

    return -EIO;
}

int littlefs_read_next_buffered(struct sensor_packet *pkt, uint16_t *out_seq_id)
{
    if (!is_mounted || !pkt || buffered_count == 0) {
        return -ENOENT;
    }

    struct fs_dir_t dirp;
    fs_dir_t_init(&dirp);
    int ret = fs_opendir(&dirp, LFS_MOUNT_POINT);
    if (ret != 0) return ret;

    struct fs_dirent entry;
    bool found = false;
    char path[48];

    while (fs_readdir(&dirp, &entry) == 0 && entry.name[0] != '\0') {
        if (entry.type == FS_DIR_ENTRY_FILE && strncmp(entry.name, "pkt_", 4) == 0) {
            snprintf(path, sizeof(path), "%s/%s", LFS_MOUNT_POINT, entry.name);
            found = true;
            break;
        }
    }
    fs_closedir(&dirp);

    if (!found) return -ENOENT;

    struct fs_file_t file;
    fs_file_t_init(&file);
    ret = fs_open(&file, path, FS_O_READ);
    if (ret != 0) return ret;

    ssize_t rd = fs_read(&file, pkt, sizeof(*pkt));
    fs_close(&file);

    if (rd == sizeof(*pkt)) {
        if (out_seq_id) *out_seq_id = pkt->seq_id;
        return 0;
    }

    return -EIO;
}

int littlefs_delete_packet(uint16_t seq_id)
{
    if (!is_mounted) return -EINVAL;

    char filename[40];
    snprintf(filename, sizeof(filename), "%s/pkt_%05u.bin", LFS_MOUNT_POINT, seq_id);

    int ret = fs_unlink(filename);
    if (ret == 0 && buffered_count > 0) {
        buffered_count--;
        LOG_DBG("Deleted buffered packet seq=%u (remaining=%zu)", seq_id, buffered_count);
    }
    return ret;
}

size_t littlefs_get_buffered_count(void)
{
    return buffered_count;
}
