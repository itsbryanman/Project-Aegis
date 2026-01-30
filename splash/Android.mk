LOCAL_PATH := $(call my-dir)

# Generate bmp.blob from splash.png for the Tegra cboot bootloader
AEGIS_SPLASH_SRC := $(LOCAL_PATH)/../splash.png
AEGIS_SPLASH_SCRIPT := $(LOCAL_PATH)/generate_bmp_blob.py

INSTALLED_BMP_BLOB_TARGET := $(PRODUCT_OUT)/bmp.blob

$(INSTALLED_BMP_BLOB_TARGET): $(AEGIS_SPLASH_SRC) $(AEGIS_SPLASH_SCRIPT)
	@echo "Generating Aegis boot splash bmp.blob"
	$(hide) python3 $(AEGIS_SPLASH_SCRIPT) --input $(AEGIS_SPLASH_SRC) --output $@

ALL_DEFAULT_INSTALLED_MODULES += $(INSTALLED_BMP_BLOB_TARGET)
