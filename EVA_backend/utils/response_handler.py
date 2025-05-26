import aiohttp
from logs.logs import logger

async def handle_response(response: aiohttp.ClientResponse) -> dict:
    """统一处理 API 响应"""
    try:
        response.raise_for_status()
        data = await response.json()
        
        # 提取标准化的响应内容
        if 'choices' in data and len(data['choices']) > 0:
            return {
                "response": data['choices'][0]['message']['content'],
                "usage": data.get('usage', {}),
                "finish_reason": data['choices'][0].get('finish_reason')
            }
        return {"error": "无效的 API 响应格式"}
    
    except aiohttp.ClientResponseError as e:
        error_info = await response.text()
        logger.error(f"API 响应错误: {e.status} - {error_info}")
        return {"error": f"HTTP {e.status}", "details": error_info}
    
    except Exception as e:
        logger.error(f"响应处理异常: {str(e)}")
        return {"error": str(e)} 