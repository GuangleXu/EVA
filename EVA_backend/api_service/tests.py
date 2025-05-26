
# EVA_backend/api_service/tests.py
from django.test import TestCase, Client
from django.urls import reverse

class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check(self):
        """测试健康检查视图"""
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})  # 只检查实际返回的内容
