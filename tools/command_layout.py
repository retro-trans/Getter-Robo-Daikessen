"""Keep native hex-menu labels and their highlights inside the left edge."""
import struct
import masm
START=0x8000DF58
LIMIT=0x8000DF80
ASM=r'''
clamp_command:
    lhu t0, 0x18(sp)
    nop
    addu t0, t0, s1
    bgtz t0, command_in_bounds
    nop
    subu s1, s1, t0
    addiu s1, s1, 1
command_in_bounds:
    jr ra
    lh v1, 0x18(s3)
'''
def assemble():
 code,labels=masm.assemble(ASM,START)
 assert START+len(code)<=LIMIT
 return code,labels

def patch_core(exe):
 import vwf
 out=bytearray(exe);_,labels=assemble()
 for address,old,new in [(0x80058104,0x8E640004,vwf.jal(labels['clamp_command'])),(0x80058108,0,0x8E640004),(0x80058310,0x86630018,vwf.jal(labels['clamp_command']))]:
  i=0x800+address-0x80010000
  assert struct.unpack_from('<I',out,i)[0]==old,hex(address)
  struct.pack_into('<I',out,i,new)
 return bytes(out)
