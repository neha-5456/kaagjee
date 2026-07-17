from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.orders.models import Order, OrderTask


class MobileOrderTaskApiTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.super_admin = self.User.objects.create_user(
            phone_number='+919999999999',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.admin = self.User.objects.create_user(
            phone_number='+919999999998',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
        )
        self.order = Order.objects.create(
            user=self.super_admin,
            total_amount=1000,
            paid_amount=0,
            pending_amount=1000,
            user_name='Test User',
            user_email='test@example.com',
            user_phone='9999999999',
        )
        self.task = OrderTask.objects.create(
            order=self.order,
            title='Pan Card Upload',
            description='Upload pan card',
            assigned_admin=self.admin,
            payment_amount=200,
            status=OrderTask.Status.ASSIGNED,
            created_by=self.super_admin,
        )

    def test_mobile_task_list_returns_only_assigned_tasks_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('orders:mobile-task-list'))

        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Pan Card Upload')
        self.assertEqual(data[0]['status'], 'assigned')

    def test_mobile_task_submit_uploads_documents_and_marks_task_completed(self):
        self.client.force_login(self.admin)
        file = SimpleUploadedFile('pan.pdf', b'pdf-bytes', content_type='application/pdf')

        response = self.client.post(
            reverse('orders:mobile-task-submit', args=[self.task.id]),
            {
                'remarks': 'Uploaded successfully',
                'status': 'completed',
                'files': [file],
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, OrderTask.Status.COMPLETED)
        self.assertEqual(self.task.remarks, 'Uploaded successfully')
        self.assertTrue(self.task.documents.exists())

    def test_mobile_task_submit_marks_task_rejected_when_requested(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('orders:mobile-task-submit', args=[self.task.id]),
            {
                'remarks': 'Need better document',
                'status': 'rejected',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, OrderTask.Status.REJECTED)
        self.assertEqual(self.task.remarks, 'Need better document')

    def test_mobile_task_submit_marks_task_rejected_via_json_payload(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('orders:mobile-task-submit', args=[self.task.id]),
            {
                'remarks': 'Need better document',
                'status': 'rejected',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, OrderTask.Status.REJECTED)
        self.assertEqual(self.task.remarks, 'Need better document')
