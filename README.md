<div align="center">

# NoneBot-Adapter-ChaoXing

_✨ 超星学习通（环信3.0） 协议适配 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/YangRucheng/nonebot-adapter-chaoxing/main/LICENSE">
    <img src="https://img.shields.io/github/license/YangRucheng/nonebot-adapter-chaoxing" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-adapter-chaoxing">
    <img src="https://img.shields.io/pypi/v/nonebot-adapter-chaoxing" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="python">
</p>

## 安装

从 PyPI 安装
```bash
pip install nonebot-adapter-chaoxing
```
或从 GitHub 仓库安装
```bash
pip install git+https://github.com/YangRucheng/nonebot-adapter-chaoxing.git#egg=nonebot-adapter-chaoxing
```

## 加载适配器

```python
import nonebot
from nonebot.adapters.chaoxing import Adapter as CxAdapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(CxAdapter)
```

## 配置 .env 文件

### 配置 Driver

```dotenv
DRIVER=~fastapi+~httpx
```

### 配置 Bot

通过 [获取用户信息 API](https://sso.chaoxing.com/apis/login/userLogin4Uname.do) 获取

```dotenv
CX_BOTS='[{
    'im_token': '',
    'im_user': '',
    'im_passwd': ''
}]'
```

## 适配情况

<div align="center">

|          | 接收消息 | 发送消息 |
| -------- | -------- | -------- |
| 文字消息 | ✅        | ✅        |
| 图片消息 | ✅        | ❌        |
| 音频消息 | ✅        | ❌        |

</div>

## 开源协议

[MIT LICENSE](https://github.com/YangRucheng/nonebot-adapter-chaoxing/blob/main/LICENSE)