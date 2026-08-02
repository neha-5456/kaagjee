from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.notifications.models import AdminNotification
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

    def test_mobile_task_submit_marks_task_accepted_and_creates_admin_notification(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('orders:mobile-task-submit', args=[self.task.id]),
            {
                'remarks': 'Task accepted by staff',
                'status': 'accepted',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, OrderTask.Status.ACCEPTED)
        self.assertEqual(self.task.remarks, 'Task accepted by staff')
        self.assertTrue(
            AdminNotification.objects.filter(
                notification_type=AdminNotification.Type.TASK_ACCEPTED,
                order_id=self.order.order_id,
                user_id=self.admin.id,
            ).exists()
        )


class SuperAdminAssignedTasksApiTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.super_admin = self.User.objects.create_user(
            phone_number='+919999999999',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.staff1 = self.User.objects.create_user(
            phone_number='+919999999998',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
        )
        self.staff2 = self.User.objects.create_user(
            phone_number='+919999999997',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
        )
        self.user = self.User.objects.create_user(
            phone_number='+919999999996',
            password='test1234',
        )
        
        # Create orders
        self.order1 = Order.objects.create(
            user=self.user,
            total_amount=1000,
            paid_amount=0,
            pending_amount=1000,
            user_name='Test User 1',
            user_email='test1@example.com',
            user_phone='9999999999',
        )
        self.order2 = Order.objects.create(
            user=self.user,
            total_amount=2000,
            paid_amount=500,
            pending_amount=1500,
            user_name='Test User 2',
            user_email='test2@example.com',
            user_phone='9999999998',
        )
        
        # Create tasks assigned to staff1
        self.task1 = OrderTask.objects.create(
            order=self.order1,
            title='Task 1',
            description='First task',
            assigned_admin=self.staff1,
            payment_amount=100,
            status=OrderTask.Status.ASSIGNED,
            created_by=self.super_admin,
        )
        self.task2 = OrderTask.objects.create(
            order=self.order2,
            title='Task 2',
            description='Second task',
            assigned_admin=self.staff1,
            payment_amount=200,
            status=OrderTask.Status.COMPLETED,
            created_by=self.super_admin,
        )
        
        # Create task assigned to staff2
        self.task3 = OrderTask.objects.create(
            order=self.order1,
            title='Task 3',
            description='Third task',
            assigned_admin=self.staff2,
            payment_amount=150,
            status=OrderTask.Status.ASSIGNED,
            created_by=self.super_admin,
        )

    def test_super_admin_can_see_all_staff_tasks_with_order_details(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('orders:super-admin-assigned-tasks'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['success'], True)
        self.assertEqual(data['summary']['total_tasks'], 3)
        self.assertEqual(data['summary']['assigned_staff_count'], 2)
        self.assertEqual(len(data['data']), 3)
        
        # Check first task has order details
        task_data = data['data'][0]
        self.assertIn('id', task_data)
        self.assertIn('order_details', task_data)
        self.assertIn('title', task_data)
        self.assertIn('status', task_data)
        self.assertIn('assigned_admin_name', task_data)
        
        # Verify order details are included
        order_details = task_data['order_details']
        self.assertIn('order_id', order_details)
        self.assertIn('total_amount', order_details)
        self.assertIn('user_name', order_details)
        self.assertIn('user_phone', order_details)

    def test_super_admin_summary_includes_staff_and_task_counts(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('orders:super-admin-assigned-tasks'))

        data = response.json()
        summary = data['summary']
        self.assertEqual(summary['total_tasks'], 3)
        self.assertEqual(summary['assigned_staff_count'], 2)
        self.assertEqual(summary['pending_tasks'], 2)  # Two ASSIGNED tasks
        self.assertEqual(summary['completed_tasks'], 1)  # One COMPLETED task
        self.assertEqual(summary['approved_tasks'], 0)
        self.assertEqual(summary['rejected_tasks'], 0)

    def test_super_admin_can_filter_tasks_by_status(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            reverse('orders:super-admin-assigned-tasks'),
            {'status': OrderTask.Status.COMPLETED}
        )

        data = response.json()
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['title'], 'Task 2')
        self.assertEqual(data['summary']['total_tasks'], 1)

    def test_super_admin_can_filter_tasks_by_staff_member(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            reverse('orders:super-admin-assigned-tasks'),
            {'admin_phone': str(self.staff1.phone_number)}
        )

        data = response.json()
        self.assertEqual(len(data['data']), 2)
        self.assertEqual(data['summary']['total_tasks'], 2)
        self.assertEqual(data['summary']['assigned_staff_count'], 1)
        
        # All tasks should be assigned to staff1
        for task in data['data']:
            self.assertEqual(task['assigned_admin_name'], 
                           getattr(self.staff1, 'full_name', None) or str(self.staff1.phone_number))


class OrdersWithAssignedTasksApiTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.super_admin = self.User.objects.create_user(
            phone_number='+919999999999',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.staff1 = self.User.objects.create_user(
            phone_number='+919999999998',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
        )
        self.staff2 = self.User.objects.create_user(
            phone_number='+919999999997',
            password='test1234',
            role=self.User.Role.ADMIN,
            is_staff=True,
        )
        self.user = self.User.objects.create_user(
            phone_number='+919999999996',
            password='test1234',
        )
        
        # Create orders
        self.order1 = Order.objects.create(
            user=self.user,
            total_amount=1000,
            paid_amount=0,
            pending_amount=1000,
            user_name='Test User 1',
            user_email='test1@example.com',
            user_phone='9999999999',
        )
        self.order2 = Order.objects.create(
            user=self.user,
            total_amount=2000,
            paid_amount=500,
            pending_amount=1500,
            user_name='Test User 2',
            user_email='test2@example.com',
            user_phone='9999999998',
        )
        self.order3 = Order.objects.create(
            user=self.user,
            total_amount=3000,
            paid_amount=0,
            pending_amount=3000,
            user_name='Test User 3',
            user_email='test3@example.com',
            user_phone='9999999997',
        )
        
        # Create tasks assigned to staff1
        self.task1 = OrderTask.objects.create(
            order=self.order1,
            title='Task 1',
            assigned_admin=self.staff1,
            status=OrderTask.Status.ASSIGNED,
            created_by=self.super_admin,
        )
        self.task2 = OrderTask.objects.create(
            order=self.order2,
            title='Task 2',
            assigned_admin=self.staff1,
            status=OrderTask.Status.COMPLETED,
            created_by=self.super_admin,
        )
        
        # Create task assigned to staff2
        self.task3 = OrderTask.objects.create(
            order=self.order2,
            title='Task 3',
            assigned_admin=self.staff2,
            status=OrderTask.Status.ASSIGNED,
            created_by=self.super_admin,
        )
        
        # Create task with no assigned admin (should not appear)
        self.task4 = OrderTask.objects.create(
            order=self.order3,
            title='Task 4',
            assigned_admin=None,
            status=OrderTask.Status.PENDING,
            created_by=self.super_admin,
        )

    def test_super_admin_can_see_all_orders_with_assigned_tasks(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('orders:orders-with-tasks'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['success'], True)
        self.assertEqual(data['summary']['total_orders'], 2)  # Only order1 and order2 have assigned tasks
        self.assertEqual(data['summary']['total_tasks'], 3)  # Total 3 assigned tasks
        self.assertEqual(len(data['data']), 2)
        
        # Each order should have its assigned tasks grouped by staff
        orders_by_id = {o['id']: o for o in data['data']}
        self.assertIn(self.order1.id, orders_by_id)
        self.assertIn(self.order2.id, orders_by_id)
        
        self.assertIn('assigned_staff_groups', orders_by_id[self.order1.id])
        self.assertEqual(len(orders_by_id[self.order1.id]['assigned_staff_groups']), 1)
        self.assertEqual(len(orders_by_id[self.order1.id]['assigned_staff_groups'][0]['tasks']), 1)

        self.assertEqual(len(orders_by_id[self.order2.id]['assigned_staff_groups']), 2)
        self.assertEqual(len(orders_by_id[self.order2.id]['assigned_staff_groups'][0]['tasks']) + len(orders_by_id[self.order2.id]['assigned_staff_groups'][1]['tasks']), 2)

    def test_staff_user_sees_only_their_own_assigned_orders(self):
        self.client.force_login(self.staff1)
        response = self.client.get(reverse('orders:orders-with-tasks'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['success'], True)
        self.assertEqual(data['summary']['total_orders'], 2)
        self.assertEqual(data['summary']['total_tasks'], 2)
        self.assertEqual(len(data['data']), 2)

        for order in data['data']:
            for staff_group in order['assigned_staff_groups']:
                self.assertEqual(staff_group['staff_id'], self.staff1.id)

    def test_orders_with_tasks_response_does_not_repeat_order_details_in_each_task(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('orders:orders-with-tasks'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['success'], True)
        self.assertGreaterEqual(len(data['data']), 1)

        first_order = data['data'][0]
        self.assertIn('assigned_staff_groups', first_order)
        first_group = first_order['assigned_staff_groups'][0]
        self.assertIn('tasks', first_group)
        self.assertGreaterEqual(len(first_group['tasks']), 1)

        first_task = first_group['tasks'][0]
        self.assertNotIn('order_details', first_task)

    def test_filter_orders_with_tasks_by_task_status(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            reverse('orders:orders-with-tasks'),
            {'task_status': OrderTask.Status.COMPLETED}
        )

        data = response.json()
        self.assertEqual(len(data['data']), 1)  # Only order2 has completed task
        self.assertEqual(data['data'][0]['id'], self.order2.id)
        # Should have only 1 task (the completed one) grouped under the relevant staff group
        self.assertEqual(len(data['data'][0]['assigned_staff_groups']), 1)
        self.assertEqual(len(data['data'][0]['assigned_staff_groups'][0]['tasks']), 1)
        self.assertEqual(data['data'][0]['assigned_staff_groups'][0]['tasks'][0]['title'], 'Task 2')

    def test_filter_orders_with_tasks_by_staff_member(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            reverse('orders:orders-with-tasks'),
            {'admin_phone': str(self.staff1.phone_number)}
        )

        data = response.json()
        self.assertEqual(len(data['data']), 2)  # order1 and order2 have staff1's tasks
        self.assertEqual(data['summary']['total_tasks'], 2)
        
        # All returned tasks should be assigned to staff1
        for order in data['data']:
            for staff_group in order['assigned_staff_groups']:
                for task in staff_group['tasks']:
                    self.assertEqual(task['assigned_admin'], self.staff1.id)
