from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Document, Group, GroupMembership, Notification, GroupInvite, JoinRequest

User = get_user_model()


class AuthenticationTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/register/'
        self.login_url = '/login/'
    
    def test_user_registration_success(self):
        data = {
            'email': 'teste@example.com',
            'password': 'senha123',
            'confirm_password': 'senha123',
            'name': 'Test User'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertEqual(response.data['email'], 'teste@example.com')
    
    def test_user_registration_password_mismatch(self):
        data = {
            'email': 'teste@example.com',
            'password': 'senha123',
            'confirm_password': 'senha456',
            'name': 'Test User'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_registration_duplicate_email(self):
        User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123'
        )
        
        data = {
            'email': 'teste@example.com',
            'password': 'senha123',
            'confirm_password': 'senha123',
            'name': 'Another User'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_success(self):
        User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123'
        )
        
        data = {
            'email': 'teste@example.com',
            'password': 'senha123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
    
    def test_user_login_invalid_credentials(self):
        data = {
            'email': 'teste@example.com',
            'password': 'senhaErrada'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123',
            first_name='Test'
        )
        self.profile_url = '/profile/'
        self.token = self._get_token()
    
    def _get_token(self):
        response = self.client.post('/login/', {
            'email': 'teste@example.com',
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_get_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'teste@example.com')
        self.assertEqual(response.data['name'], 'Test')
    
    def test_update_profile_name(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        data = {
            'name': 'New Name',
            'current_password': 'senha123'
        }
        response = self.client.patch(self.profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New Name')
    
    def test_update_profile_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        data = {
            'current_password': 'senha123',
            'new_password': 'novaSenha123',
            'confirm_password': 'novaSenha123'
        }
        response = self.client.patch(self.profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica que a nova password funciona
        login_response = self.client.post('/login/', {
            'email': 'teste@example.com',
            'password': 'novaSenha123'
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)


class NotificationTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123'
        )
        self.notifications_url = '/notifications/'
        self.count_url = '/notifications/count/'
        self.token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def _get_token(self):
        response = self.client.post('/login/', {
            'email': 'teste@example.com',
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_list_empty_notifications(self):
        response = self.client.get(self.notifications_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_create_notification(self):
        data = {
            'notification_type': 'SYSTEM',
            'title': 'Test Notification',
            'message': 'This is a test notification'
        }
        response = self.client.post(self.notifications_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['title'], 'Test Notification')
        self.assertEqual(response.data['is_read'], False)
    
    def test_get_notification_count(self):
        # Cria 2 notificações
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 1',
            message='Message 1'
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 2',
            message='Message 2',
            is_read=True
        )
        
        response = self.client.get(self.count_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 2)
        self.assertEqual(response.data['unread_count'], 1)
    
    def test_mark_notification_as_read(self):
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test',
            message='Message'
        )
        
        response = self.client.put(f'{self.notifications_url}{notif.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_read'], True)
        self.assertIsNotNone(response.data['read_at'])
    
    def test_delete_notification(self):
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test',
            message='Message'
        )
        
        response = self.client.delete(f'{self.notifications_url}{notif.id}/delete/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())
    
    def test_mark_all_as_read(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 1',
            message='Message 1'
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 2',
            message='Message 2'
        )
        
        response = self.client.put(f'{self.notifications_url}mark-all-as-read/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        
        # Verifica que todas são lidas
        unread = Notification.objects.filter(recipient=self.user, is_read=False)
        self.assertEqual(unread.count(), 0)
    
    def test_delete_all_notifications(self):
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 1',
            message='Message 1'
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            title='Test 2',
            message='Message 2'
        )
        
        response = self.client.delete(f'{self.notifications_url}delete-all/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)
        
        # Verifica que não há notificações
        count = Notification.objects.filter(recipient=self.user).count()
        self.assertEqual(count, 0)


class DocumentTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123'
        )
        self.documents_url = '/documents/'
        self.token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def _get_token(self):
        response = self.client.post('/login/', {
            'email': 'teste@example.com',
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_list_empty_documents(self):
        response = self.client.get(self.documents_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_list_documents(self):
        Document.objects.create(
            user=self.user,
            filename='test.pdf',
            state='DONE'
        )
        
        response = self.client.get(self.documents_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['filename'], 'test.pdf')


class GroupTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='teste@example.com',
            email='teste@example.com',
            password='senha123'
        )
        self.user2 = User.objects.create_user(
            username='user2@example.com',
            email='user2@example.com',
            password='senha123'
        )
        self.groups_url = '/groups/'
        self.token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def _get_token(self):
        response = self.client.post('/login/', {
            'email': 'teste@example.com',
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_create_group(self):
        data = {
            'name': 'Test Group'
        }
        response = self.client.post(f'{self.groups_url}create/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Group')
        self.assertIn('invite_code', response.data)
    
    def test_list_my_groups(self):
        group = Group.objects.create(name='Test Group', owner=self.user)
        GroupMembership.objects.create(user=self.user, group=group, role='owner')
        
        response = self.client.get(f'{self.groups_url}my/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Group')
        self.assertEqual(response.data[0]['role'], 'owner')
    
    def test_get_group_members(self):
        group = Group.objects.create(name='Test Group', owner=self.user)
        GroupMembership.objects.create(user=self.user, group=group, role='owner')
        GroupMembership.objects.create(user=self.user2, group=group, role='member')
        
        response = self.client.get(f'{self.groups_url}{group.id}/members/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_invite_member_to_group(self):
        group = Group.objects.create(name='Test Group', owner=self.user)
        GroupMembership.objects.create(user=self.user, group=group, role='owner')
        
        data = {
            'email': self.user2.email
        }
        response = self.client.post(f'{self.groups_url}{group.id}/invite/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('invite_id', response.data)
    
    def test_duplicate_group_name(self):
        Group.objects.create(name='Test Group', owner=self.user)
        
        data = {
            'name': 'Test Group'
        }
        response = self.client.post(f'{self.groups_url}create/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticationRequiredTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
    
    def test_notifications_without_auth(self):
        response = self.client.get('/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_without_auth(self):
        response = self.client.get('/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_documents_without_auth(self):
        response = self.client.get('/documents/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GroupAccessTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1@example.com',
            email='user1@example.com',
            password='senha123'
        )
        self.user2 = User.objects.create_user(
            username='user2@example.com',
            email='user2@example.com',
            password='senha123'
        )
        self.group = Group.objects.create(name='Private Group', owner=self.user1)
        GroupMembership.objects.create(user=self.user1, group=self.group, role='owner')
        
        self.token1 = self._get_token('user1@example.com')
        self.token2 = self._get_token('user2@example.com')
    
    def _get_token(self, email):
        response = self.client.post('/login/', {
            'email': email,
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_user_cannot_access_other_group(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get(f'/groups/{self.group.id}/members/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class GroupInviteTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='senha123'
        )
        self.invitee = User.objects.create_user(
            username='invitee@example.com',
            email='invitee@example.com',
            password='senha123'
        )
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        GroupMembership.objects.create(user=self.owner, group=self.group, role='owner')
        
        self.owner_token = self._get_token('owner@example.com')
        self.invitee_token = self._get_token('invitee@example.com')
    
    def _get_token(self, email):
        response = self.client.post('/login/', {
            'email': email,
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_accept_invite(self):
        # Owner envia convite
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.owner_token}')
        invite_response = self.client.post(
            f'/groups/{self.group.id}/invite/',
            {'email': self.invitee.email},
            format='json'
        )
        self.assertEqual(invite_response.status_code, status.HTTP_201_CREATED)
        invite_id = invite_response.data['invite_id']
        
        # Invitee aceita convite
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.invitee_token}')
        accept_response = self.client.post(f'/groups/invites/{invite_id}/accept/')
        
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        
        # Verificar que invitee é agora membro do grupo
        membership = GroupMembership.objects.filter(
            user=self.invitee,
            group=self.group
        )
        self.assertTrue(membership.exists())
        self.assertEqual(membership.first().role, 'member')


class GroupJoinTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='senha123'
        )
        self.joiner = User.objects.create_user(
            username='joiner@example.com',
            email='joiner@example.com',
            password='senha123'
        )
        self.group = Group.objects.create(name='Public Group', owner=self.owner)
        GroupMembership.objects.create(user=self.owner, group=self.group, role='owner')
        
        self.owner_token = self._get_token('owner@example.com')
        self.joiner_token = self._get_token('joiner@example.com')
    
    def _get_token(self, email):
        response = self.client.post('/login/', {
            'email': email,
            'password': 'senha123'
        }, format='json')
        return response.data['tokens']['access']
    
    def test_join_group_by_code(self):
        invite_code = str(self.group.invite_code)
        
        # Joiner faz pedido para juntar-se
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.joiner_token}')
        join_response = self.client.post(f'/groups/join/{invite_code}/')
        
        self.assertEqual(join_response.status_code, status.HTTP_201_CREATED)
        request_id = join_response.data['request_id']
        
        # Owner aprova o pedido
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.owner_token}')
        approve_response = self.client.post(f'/groups/join-requests/{request_id}/approve/')
        
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        
        # Verificar que joiner é agora membro
        membership = GroupMembership.objects.filter(
            user=self.joiner,
            group=self.group
        )
        self.assertTrue(membership.exists())
        self.assertEqual(membership.first().role, 'member')
