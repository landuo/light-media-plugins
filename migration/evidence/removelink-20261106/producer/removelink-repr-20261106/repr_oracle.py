import sys,json,hashlib,unicodedata
# CPython builtin repr is the actual list-log formatter called by the installed
# AST. No target formatter or target-generated expected data is imported.
contexts=['',"'",'"',"'\"\\"]
h=hashlib.sha256();count=0
for cp in range(0x110000):
    if 0xD800 <= cp <= 0xDFFF: continue
    for prefix in contexts:
        h.update((repr(prefix+chr(cp))+'\n').encode('utf-8'))
        count+=1
samples=['',"'",'"',"'\"",'\\',"a'b",'a"b',"a'\"b\\",'\a\b\t\n\v\f\r', ''.join(chr(x) for x in range(32)),chr(127),chr(133),chr(160),' \u1680\u2000\u200b\u2028\u2029\u202f\u3000', '\u00ad\u061c\u200d\u2060\ufeff','\u0378\ue000\ufffe\uffff','\U0001f600\U000e0001\U000f0000\U0010ffff','中文café𝄞e\u0301']
print(json.dumps({'runtime':sys.version,'unicode_version':unicodedata.unidata_version,'classification':'actual fixed installed CPython builtin repr, all Unicode scalar values and four quote contexts; no app or target import/network','contexts':contexts,'scalar_count':0x110000-0x800,'repr_count':count,'repr_sha256':h.hexdigest(),'cases':[{'value':v,'repr':repr(v)} for v in samples],'lists':[{'values':xs,'repr':repr(xs)} for xs in [[],samples[:8],samples[8:],['first','second',"third's",'fourth"s']]]},ensure_ascii=True))
