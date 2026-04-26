import logging

logger = logging.getLogger(__name__)

def parse_proxy_url(proxy_url: str):
    """
    将数据库中存储的代理连接字符串转换为 Playwright 可识别的 proxy 字典配置。
    支持格式:
        1. http://123.45.67.89:8080
        2. http://username:password@123.45.67.89:8080
    
    返回字典结构:
    {
        "server": "http://123.45.67.89:8080",
        "username": "username",
        "password": "password"
    }
    """
    if not proxy_url:
        return None

    proxy_url = proxy_url.strip()
    
    try:
        # 如果带有用户名和密码 (包含 @ 符号)
        if "@" in proxy_url:
            # 拆分协议+鉴权信息 与 IP+端口
            proto_auth, host_port = proxy_url.split("@", 1)
            # proto_auth => http://username:password
            proto, auth = proto_auth.split("://", 1)
            username, password = auth.split(":", 1)
            
            # Playwright server 参数只接受协议+IP+端口
            server = f"{proto}://{host_port}"
            
            return {
                "server": server,
                "username": username,
                "password": password
            }
        else:
            # 没有密码的白名单代理模式
            return {
                "server": proxy_url
            }
    except Exception as e:
        logger.error(f"解析代理 URL ({proxy_url}) 失败: {e}")
        return None
