# Makefile for AzamLabs Cisco IOL 100:1 CPU Idle Governor Shim
CC ?= gcc
CFLAGS = -Wall -O2 -fPIC -shared
LDFLAGS = -ldl

TARGET_64 = azam-iol-shim.so
TARGET_32 = azam-iol-shim32.so

all: $(TARGET_64)

$(TARGET_64): azam-iol-shim.c
	$(CC) $(CFLAGS) -m64 -o $@ $< $(LDFLAGS)

32bit: $(TARGET_32)

$(TARGET_32): azam-iol-shim.c
	$(CC) $(CFLAGS) -m32 -o $@ $< $(LDFLAGS)

install: $(TARGET_64)
	mkdir -p /opt/azamlabs/lib
	cp $(TARGET_64) /opt/azamlabs/lib/
	@if [ -f $(TARGET_32) ]; then cp $(TARGET_32) /opt/azamlabs/lib/; fi

clean:
	rm -f $(TARGET_64) $(TARGET_32)
