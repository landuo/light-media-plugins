# OCR JSON 结果与表单有限切片

5份consumer候选与固定前像见production-files.json，reproduce_candidates.py可逐字节重放5个hunk。后端/SDK已经由Root的privacy+OCR6真实代码供应；本片不改host生产文件，不覆盖F1/F2记值、owner和原始来源引用。

原完整OcrHelper/RequestUtils/Requests：60条件/105实际HTTP；原完整HDSky.signin：14条件/80实际HTTP，保留实际1秒sleep。新安装SDK worker→真实App/引用/配置→生产OCRSignin与SourceDo→owned TLS/HTTP服务，74条件/185请求、75 named、0 skip，全部结果/异常/方法/头/体相同。它是合成服务协议回放和真实宿主链，不是外部OCR识别或真实PT验收。

覆盖NaN/Inf/overflow、超大int、真假值、字典顺序/重复键、doseq/None、lone codepoints/UTF8位置和深层数据。JSON parser原界保持；OCR RequestUtils表单repr的非空child深度9993/9994及空终端早返由实际源确定。原值直接留在进程内，不重入strict JSON，不新增解释器或转换框架。

旧binding控制41 leaf真实失败；旧strict parser的七短条件正常Go FAIL exit1，其中3 leaf真实失败、4控制成功。旧完整深度控制过慢被自建容器精确强停，不计业务红；第一次wire缺字段、daemon未启动、fixture sourceException级联和shell正则启动错误全部保留。

纯63 named race与Linux App75 named正常门分别计证。本片未签App race、OpenCD全JSON调用、浏览器、Main/UI或全AutoSignIn。既有载荷/URL/form数量上限仍列为平台适配。
