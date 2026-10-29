import struct
import pytest
from minerva.live import crc16_mcrf4xx, encode_mavlink_v2_frame, parse_mavlink_v2_datagram


def reference_crc(data):
    value = 0xffff
    for byte in data:
        temp = byte ^ (value & 255)
        temp ^= (temp << 4) & 255
        value = ((value >> 8) ^ (temp << 8) ^ (temp << 3) ^ (temp >> 4)) & 65535
    return value


def test_crc_reference():
    assert crc16_mcrf4xx(b'123456789',50)==reference_crc(b'123456789'+bytes([50]))
    for n in range(256):
        data = bytes(range(n))
        assert crc16_mcrf4xx(data,104)==reference_crc(data+bytes([104]))


def test_trim_relative_alt_and_multiple_frames():
    payload = struct.pack('<IiiiihhhH',1234,501000000,-1114000000,900000,120000,0,0,0,0)
    position = encode_mavlink_v2_frame(33,payload,7,2,19)
    heartbeat = encode_mavlink_v2_frame(0,bytes(9))
    assert heartbeat[1]==1 and position[1]<28
    decoded,dropped = parse_mavlink_v2_datagram(heartbeat+position)
    assert dropped==0 and len(decoded)==2
    assert decoded[1]['alt_m']==120 and decoded[1]['alt']==900000
    assert decoded[1]['sysid']==7 and decoded[1]['compid']==2 and decoded[1]['seq']==19
    assert decoded[1]['lat_deg']==50.1 and decoded[1]['lon_deg']==-111.4


def test_signed_policy_and_drops():
    frame = bytearray(encode_mavlink_v2_frame(0,bytes(9)))
    frame[2]=1
    frame[-2:] = struct.pack('<H',crc16_mcrf4xx(bytes(frame[1:-2]),50))
    signed = bytes(frame)+bytes(13)
    messages,dropped = parse_mavlink_v2_datagram(signed+encode_mavlink_v2_frame(0,bytes(9)))
    assert dropped==0 and len(messages)==2
    assert messages[0]['trust']=='not authenticated'
    for bad in [signed[:-1],b'garbage',b'\xfd',bytes(frame[:-2])+b'\0\0'+bytes(13)]:
        messages,dropped = parse_mavlink_v2_datagram(bad)
        assert messages==[] and dropped==1
    frame[2]=2
    assert parse_mavlink_v2_datagram(bytes(frame))[1]==1
    with pytest.raises(ValueError): encode_mavlink_v2_frame(33,b'')
