import signal
import socket
import time
import psutil
from logs.logs import logger 


class PortManager:
    """
    端口管理器类
    负责管理应用程序的端口使用、检测和清理
    """

    def __init__(self, port):
        """
        初始化端口管理器
        @param port: 需要管理的端口号
        """
        # 基础配置参数
        self.port = port  # 内部服务端口
        logger.system(f"端口管理器初始化中，内部端口: {self.port}")
        self.max_attempts = 3  # 最大重试次数
        self.wait_time = 2  # 重试等待时间(秒)
        self.timeout = 10  # 重试超时时间(秒)

        # 初始化信号处理
        self.setup_signal_handlers()
        logger.system(f"端口管理器初始化完成，内部端口: {self.port}")

    def is_port_in_use(self):
        """
        检查端口是否被占用
        @return: bool 端口是否被占用
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(("127.0.0.1", self.port))
                return False  # 端口未被占用
        except (socket.error, OSError):
            return True  # 端口被占用

    def _find_process_using_port(self):
        """
        查找使用指定端口的进程
        @return: psutil.Process 或 None
        """
        try:
            for proc in psutil.process_iter(["pid", "name", "connections"]):
                try:
                    for conn in proc.connections():
                        if conn.laddr.port == self.port:
                            return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue  # 忽略无权限或已终止的进程
        except Exception as e:
            logger.error(f"查找进程时出错: {str(e)}")
        return None

    def _kill_process_on_port(self):
        """
        终止占用端口的进程
        @return: bool 是否成功终止
        """
        process = self._find_process_using_port()
        if not process:
            return True  # 没有找到占用端口的进程
        try:
            logger.system(f"尝试终止进程 PID:{process.pid} ({process.name()})")
            process.terminate()  # 发送终止信号
            try:
                process.wait(timeout=3)  # 等待进程终止
            except psutil.TimeoutExpired:
                logger.warning("进程未响应终止信号,强制结束")
                process.kill()  # 强制结束进程
            return True
        except Exception as e:
            logger.error(f"终止进程失败: {str(e)}")
            return False

    def wait_for_port_release(self):
        """
        等待端口释放
        @return: bool 端口是否成功释放
        """
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if not self.is_port_in_use():
                logger.system(f"端口 {self.port} 已释放")
                return True
            time.sleep(0.5)
        logger.error(f"等待端口释放超时")
        return False

    def ensure_port_available(self):
        """
        确保端口可用
        包含重试机制的端口可用性检查
        @return: bool 是否成功确保端口可用
        """
        attempts = 0
        while attempts < self.max_attempts:
            if not self.is_port_in_use():
                logger.system(f"端口 {self.port} 可用")
                return True
            logger.warning(
                f"端口 {self.port} 被占用 (尝试 {attempts + 1}/{self.max_attempts})"
            )
            if self._kill_process_on_port():
                if self.wait_for_port_release():
                    return True

            attempts += 1
            if attempts < self.max_attempts:
                time.sleep(self.wait_time)
        logger.error(f"无法确保端口 {self.port} 可用")
        return False

    def setup_signal_handlers(self):
        """
        设置进程信号处理器
        用于捕获终止信号,实现优雅关闭
        """
        signal.signal(signal.SIGTERM, self.handle_shutdown)  # 终止信号
        signal.signal(signal.SIGINT, self.handle_shutdown)  # 中断信号
        logger.debug("信号处理器设置完成")

    def handle_shutdown(self, signum, frame):
        """
        处理关闭信号
        @param signum: 信号数字
        @param frame: 当前栈帧
        """
        logger.system("接收到关闭信号,正在清理端口...")
        self.cleanup()

    def cleanup(self):
        """
        清理资源
        在应用程序关闭时调用
        """
        try:
            if self.is_port_in_use():
                if self._kill_process_on_port():
                    logger.system(f"成功清理端口 {self.port}")
                else:
                    logger.warning(f"清理端口 {self.port} 失败")
            else:
                logger.system(f"端口 {self.port} 未被占用,无需清理")
        except Exception as e:
            logger.error(f"清理过程发生错误: {str(e)}")
