"""New upstream API drivers and Python oracles; no previous study is edited."""
import json
import struct
import xml.etree.ElementTree as ET

import numpy as np

from src.benchmarks.region import COMMON, HASH_C, BASIS, feed, string_hash, semantic_json

JSONPARSER = COMMON + HASH_C + r'''
#include "json.h"
static uint64_t walk(uint64_t h,json_value *v){
 switch(v->type){
 case json_null:return feed(h,1);
 case json_boolean:return feed(feed(h,2),v->u.boolean!=0);
 case json_integer:return feed(feed(h,3),(uint64_t)v->u.integer);
 case json_string:return string_hash(feed(h,4),v->u.string.ptr,v->u.string.length);
 case json_array:h=feed(feed(h,5),v->u.array.length);
  for(unsigned i=0;i<v->u.array.length;i++)h=walk(h,v->u.array.values[i]);return h;
 case json_object:h=feed(feed(h,6),v->u.object.length);
  for(unsigned i=0;i<v->u.object.length;i++){json_object_entry *e=&v->u.object.values[i];h=walk(string_hash(h,e->name,e->name_length),e->value);}return h;
 default:exit(3);}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);START();
 json_value *v=json_parse((const char*)input,length);STOP();if(!v)return 3;
 uint64_t h=walk(UINT64_C(1469598103934665603),v);json_value_free(v);nc_emit_u64(h);return 0;}
'''

JSONH = COMMON + HASH_C + r'''
#include "json.h"
static uint64_t walk(uint64_t h,struct json_value_s *v){
 switch(v->type){
 case json_type_null:return feed(h,1);
 case json_type_true:return feed(feed(h,2),1);
 case json_type_false:return feed(feed(h,2),0);
 case json_type_number:{struct json_number_s *n=v->payload;return feed(feed(h,3),(uint64_t)strtoll(n->number,NULL,10));}
 case json_type_string:{struct json_string_s *s=v->payload;return string_hash(feed(h,4),s->string,s->string_size);}
 case json_type_array:{struct json_array_s *a=v->payload;h=feed(feed(h,5),a->length);
  for(struct json_array_element_s *e=a->start;e;e=e->next)h=walk(h,e->value);return h;}
 case json_type_object:{struct json_object_s *o=v->payload;h=feed(feed(h,6),o->length);
  for(struct json_object_element_s *e=o->start;e;e=e->next)h=walk(string_hash(h,e->name->string,e->name->string_size),e->value);return h;}
 default:exit(3);}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);START();
 struct json_value_s *v=json_parse(input,length);STOP();if(!v)return 3;
 uint64_t h=walk(UINT64_C(1469598103934665603),v);free(v);nc_emit_u64(h);return 0;}
'''

FROZEN = COMMON + HASH_C + r'''
#include "frozen.h"
typedef struct {uint64_t hash;unsigned depth;int containers[64];} state;
static void callback(void *p,const char *name,size_t n,const char *path,const struct json_token *t){
 (void)path;state *s=p;uint64_t *h=&s->hash;
 int end=t->type==JSON_TYPE_ARRAY_END||t->type==JSON_TYPE_OBJECT_END;
 if(!end&&s->depth&&s->containers[s->depth-1]==6){if(!name)exit(3);*h=string_hash(*h,name,n);}
 switch(t->type){
 case JSON_TYPE_NULL:*h=feed(*h,1);break;
 case JSON_TYPE_TRUE:*h=feed(feed(*h,2),1);break;
 case JSON_TYPE_FALSE:*h=feed(feed(*h,2),0);break;
 case JSON_TYPE_NUMBER:*h=feed(feed(*h,3),(uint64_t)strtoll(t->ptr,NULL,10));break;
 case JSON_TYPE_STRING:*h=string_hash(feed(*h,4),t->ptr,t->len);break;
 case JSON_TYPE_ARRAY_START:if(s->depth==64)exit(3);s->containers[s->depth++]=5;*h=feed(*h,5);break;
 case JSON_TYPE_OBJECT_START:if(s->depth==64)exit(3);s->containers[s->depth++]=6;*h=feed(*h,6);break;
 case JSON_TYPE_ARRAY_END:if(!s->depth||s->containers[--s->depth]!=5)exit(3);*h=feed(*h,7);break;
 case JSON_TYPE_OBJECT_END:if(!s->depth||s->containers[--s->depth]!=6)exit(3);*h=feed(*h,8);break;
 default:exit(3);}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);state s={.hash=UINT64_C(1469598103934665603)};
 START();int rc=json_walk((const char*)input,(int)length,callback,&s);STOP();if(rc<0||s.depth)return 3;nc_emit_u64(s.hash);return 0;}
'''

YXML = COMMON + HASH_C + r'''
#include "yxml.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);yxml_t x;char stack[4096];
 uint64_t h=UINT64_C(1469598103934665603);START();yxml_init(&x,stack,sizeof(stack));
 for(size_t i=0;i<length;i++){int t=yxml_parse(&x,input[i]);if(t<0)return 3;
  if(t==YXML_ELEMSTART)h=string_hash(feed(h,1),x.elem,strlen(x.elem));
  else if(t==YXML_ELEMEND)h=feed(h,2);
  else if(t==YXML_CONTENT)for(const unsigned char *p=(unsigned char*)x.data;*p;p++)h=feed(feed(h,3),*p);
 }
 int rc=yxml_eof(&x);STOP();if(rc<0)return 3;nc_emit_u64(h);return 0;}
'''

MPACK = COMMON + HASH_C + r'''
#include "mpack.h"
static uint64_t walk(uint64_t h,mpack_node_t v){switch(mpack_node_type(v)){
 case mpack_type_nil:return feed(h,1);
 case mpack_type_bool:return feed(feed(h,2),mpack_node_bool(v));
 case mpack_type_uint:return feed(feed(h,3),mpack_node_u64(v));
 case mpack_type_int:return feed(feed(h,3),(uint64_t)mpack_node_i64(v));
 case mpack_type_str:return string_hash(feed(h,4),mpack_node_str(v),mpack_node_strlen(v));
 case mpack_type_array:{size_t n=mpack_node_array_length(v);h=feed(feed(h,5),n);for(size_t i=0;i<n;i++)h=walk(h,mpack_node_array_at(v,i));return h;}
 case mpack_type_map:{size_t n=mpack_node_map_count(v);h=feed(feed(h,6),n);for(size_t i=0;i<n;i++){
  mpack_node_t k=mpack_node_map_key_at(v,i);h=walk(string_hash(h,mpack_node_str(k),mpack_node_strlen(k)),mpack_node_map_value_at(v,i));}return h;}
 default:exit(3);}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);mpack_tree_t tree;START();
 mpack_tree_init_data(&tree,(const char*)input,length);mpack_tree_parse(&tree);STOP();
 if(mpack_tree_error(&tree)!=mpack_ok)return 3;uint64_t h=walk(UINT64_C(1469598103934665603),mpack_tree_root(&tree));
 if(mpack_tree_destroy(&tree)!=mpack_ok)return 3;nc_emit_u64(h);return 0;}
'''

ROUNDTRIP_END = r'''
 if(out!=length||memcmp(plain,input,length))return 3;
 uint64_t h=UINT64_C(1469598103934665603);for(size_t i=0;i<out;i++)h=feed(h,plain[i]);
 const char *dump=getenv("NC_VERIFY_STREAM");if(dump){FILE *f=fopen(dump,"wb");if(!f)return 3;
  if(fwrite(packed,1,size,f)!=size||fclose(f))return 3;}
 nc_emit_u64(h);free(packed);free(plain);return 0;}
'''

MINIZ = COMMON + HASH_C + r'''
#include "miniz.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);mz_ulong bound=mz_compressBound(length),size=bound,out=length;
 unsigned char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int a=mz_compress2(packed,&size,input,length,6);int b=mz_uncompress(plain,&out,packed,size);STOP();
 if(a!=MZ_OK||b!=MZ_OK||size<1)return 3;
''' + ROUNDTRIP_END

FASTLZ = COMMON + HASH_C + r'''
#include "fastlz.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);unsigned char *packed=malloc(length+length/10+1024),*plain=malloc(length);
 if(!packed||!plain)return 2;START();int size=fastlz_compress_level(1,input,(int)length,packed);
 int out=fastlz_decompress(packed,size,plain,(int)length);STOP();if(size<1||out<1)return 3;
''' + ROUNDTRIP_END

LIBDEFLATE = COMMON + HASH_C + r'''
#include "libdeflate.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);
 struct libdeflate_compressor *c=libdeflate_alloc_compressor(6);struct libdeflate_decompressor *d=libdeflate_alloc_decompressor();
 if(!c||!d)return 2;size_t bound=libdeflate_zlib_compress_bound(c,length),out=0;
 unsigned char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();size_t size=libdeflate_zlib_compress(c,input,length,packed,bound);
 enum libdeflate_result rc=libdeflate_zlib_decompress(d,packed,size,plain,length,&out);STOP();
 libdeflate_free_compressor(c);libdeflate_free_decompressor(d);if(size<1||rc!=LIBDEFLATE_SUCCESS)return 3;
''' + ROUNDTRIP_END

ZLIB = COMMON + HASH_C + r'''
#include "zlib.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);uLong bound=compressBound(length);uLongf size=bound,out=length;
 unsigned char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int a=compress2(packed,&size,input,length,6);int b=uncompress(plain,&out,packed,size);STOP();
 if(a!=Z_OK||b!=Z_OK||size<1)return 3;
''' + ROUNDTRIP_END

LZ4 = COMMON + HASH_C + r'''
#include "lz4.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);int bound=LZ4_compressBound((int)length);
 unsigned char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int size=LZ4_compress_default((const char*)input,(char*)packed,(int)length,bound);
 int out=LZ4_decompress_safe((const char*)packed,(char*)plain,size,(int)length);STOP();if(size<1||out<1)return 3;
''' + ROUNDTRIP_END

DRIVERS = {'jsonparser': JSONPARSER, 'jsonh': JSONH, 'frozen': FROZEN, 'yxml': YXML,
           'mpack': MPACK, 'miniz': MINIZ, 'fastlz': FASTLZ, 'libdeflate': LIBDEFLATE,
           'zlib': ZLIB, 'lz4': LZ4}


def structured(variant):
    records = [{'id': i, 'name': f'item{i}', 'values': [i, i * 7, True, None]} for i in range(3000)]
    return records if variant == 'flat' else {'records': records, 'meta': {'enabled': False, 'groups': [[i, i + 1] for i in range(1000)]}}


def pack(value):
    """Small specification-based MessagePack encoder, independent of MPack."""
    if value is None: return b'\xc0'
    if isinstance(value, bool): return b'\xc3' if value else b'\xc2'
    if isinstance(value, int):
        if 0 <= value < 128: return bytes([value])
        if -32 <= value < 0: return bytes([value & 255])
        return b'\xd3' + struct.pack('>q', value)
    if isinstance(value, str):
        data = value.encode(); n = len(data)
        return (bytes([0xa0 + n]) if n < 32 else b'\xdb' + struct.pack('>I', n)) + data
    if isinstance(value, list):
        n = len(value); return (bytes([0x90 + n]) if n < 16 else b'\xdd' + struct.pack('>I', n)) + b''.join(pack(v) for v in value)
    if isinstance(value, dict):
        n = len(value); return (bytes([0x80 + n]) if n < 16 else b'\xdf' + struct.pack('>I', n)) + b''.join(pack(k) + pack(v) for k, v in value.items())
    raise ValueError('Unsupported MessagePack fixture type')


def sax(value, h=BASIS):
    if value is None: return feed(h, 1)
    if isinstance(value, bool): return feed(feed(h, 2), value)
    if isinstance(value, int): return feed(feed(h, 3), value)
    if isinstance(value, str): return string_hash(feed(h, 4), value)
    if isinstance(value, list):
        h = feed(h, 5)
        for child in value: h = sax(child, h)
        return feed(h, 7)
    if isinstance(value, dict):
        h = feed(h, 6)
        for key, child in value.items(): h = sax(child, string_hash(h, key))
        return feed(h, 8)
    raise ValueError('Unsupported SAX oracle type')


def xml_hash(data):
    def walk(node, h):
        h = string_hash(feed(h, 1), node.tag)
        for byte in (node.text or '').encode(): h = feed(feed(h, 3), byte)
        for child in node:
            h = walk(child, h)
            for byte in (child.tail or '').encode(): h = feed(feed(h, 3), byte)
        return feed(h, 2)
    return walk(ET.fromstring(data), BASIS)


def input_bytes(case):
    program, variant = case.split('_', 1)
    if program in ['jsonparser', 'jsonh', 'frozen', 'mpack']:
        value = structured(variant)
        return pack(value) if program == 'mpack' else json.dumps(value, separators=(',', ':')).encode()
    if program == 'yxml':
        body = ''.join(f'<item><id>{i}</id><name>item{i}&amp;data</name></item>' for i in range(3000))
        return ('<root>' + (body if variant == 'flat' else '<group>' + body + '</group>') + '</root>').encode()
    if program in ['miniz', 'fastlz', 'libdeflate', 'zlib', 'lz4']:
        n = 2 * 1024 * 1024
        if variant == 'random': return np.random.default_rng(20261012).integers(0, 256, n, dtype=np.uint8).tobytes()
        phrase = b'Portable independently checked compression workload 0123456789\n'
        return (phrase * (n // len(phrase) + 1))[:n]
    raise ValueError('Unregistered expanded case')


def oracle(case):
    program, variant = case.split('_', 1); data = input_bytes(case)
    if program in ['jsonparser', 'jsonh', 'mpack']: return semantic_json(structured(variant))
    if program == 'frozen': return sax(json.loads(data))
    if program == 'yxml': return xml_hash(data)
    h = BASIS
    for byte in data: h = feed(h, byte)
    return h


def decode_fastlz(data, limit):
    """Independent FastLZ level-1 decoder, including overlapping matches."""
    if not data or data[0] >> 5: raise ValueError('Not a level-1 stream')
    out = bytearray(); pos = 1; control = data[0]
    def take():
        nonlocal pos
        if pos >= len(data): raise ValueError('Truncated FastLZ stream')
        v = data[pos]; pos += 1; return v
    while True:
        if control < 32:
            n = control + 1
            if pos + n > len(data): raise ValueError('Truncated literal')
            out.extend(data[pos:pos+n]); pos += n
        else:
            n = (control >> 5) - 1
            if n == 6: n += take()
            offset = ((control & 31) << 8) + take() + 1; n += 3
            if offset > len(out): raise ValueError('Invalid backreference')
            for _ in range(n): out.append(out[-offset])
        if len(out) > limit: raise ValueError('Output exceeds bound')
        if pos == len(data): return bytes(out)
        control = take()
