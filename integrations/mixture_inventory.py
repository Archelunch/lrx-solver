"""Read numeric NPZ data with stdlib only; never unpickle or execute source."""
import ast
import io
import json
import struct
import zipfile


def bool_matrix(data):
    if data[:8]!=b'\x93NUMPY\x01\x00':raise ValueError('only NPY v1 supported')
    size=struct.unpack('<H',data[8:10])[0];header=ast.literal_eval(data[10:10+size].decode('ascii'))
    if header!={'descr':'|b1','fortran_order':False,'shape':(40320,512)}:raise ValueError('unexpected boolean matrix')
    payload=data[10+size:]
    if len(payload)!=40320*512 or any(x not in (0,1) for x in payload):raise ValueError('invalid boolean payload')
    return payload


def residual_inventory(archive):
    with zipfile.ZipFile(archive) as z:
        result=json.loads(z.read('literature/multiset_nine_gap_projection_search_20260924.json'))
        with zipfile.ZipFile(io.BytesIO(z.read('literature/multiset_nine_gap_projection_search_20260924.npz'))) as arrays:
            union=bool_matrix(arrays.read('union_covered.npy'))
    masks={}
    for row in result['residual']:
        raw=bytes.fromhex(row['order_bits_hex'])
        if len(raw)!=5040:raise ValueError('invalid residual bitset size')
        bits=int.from_bytes(raw,'little')
        if bits.bit_count()!=row['count']:raise ValueError('residual count mismatch')
        mask=row['mask']
        if not 1<=mask<512 or mask in masks:raise ValueError('invalid/duplicate mask')
        if any(((raw[i//8]>>(i%8))&1)!=1-union[i*512+mask] for i in range(40320)):
            raise ValueError('residual bitset/table disagreement')
        masks[mask]=bits
    if sum(b.bit_count() for b in masks.values())!=result['remaining']:raise ValueError('remaining count mismatch')
    return masks
