from django.test import TestCase
from django.urls import reverse
from .models import State, City


class StateListViewTests(TestCase):
    def test_state_search_filters_by_name(self):
        State.objects.create(name='Maharashtra', slug='maharashtra', code='MH', is_active=True)
        State.objects.create(name='Delhi', slug='delhi', code='DL', is_active=True)

        url = reverse('locations:state-list')
        response = self.client.get(url, {'search': 'Mah'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get('results', response.json().get('data', []))), 1)
        self.assertEqual(response.json()['results'][0]['code'], 'MH')


class CityListViewTests(TestCase):
    def test_city_search_filters_by_name(self):
        state = State.objects.create(name='Maharashtra', slug='maharashtra', code='MH', is_active=True)
        City.objects.create(name='Pune', slug='pune', tier='tier_2', is_popular=False, state=state, is_active=True)
        City.objects.create(name='Mumbai', slug='mumbai', tier='tier_1', is_popular=False, state=state, is_active=True)

        url = reverse('locations:city-list')
        response = self.client.get(url, {'search': 'Pun'})

        self.assertEqual(response.status_code, 200)
        data = response.json().get('results', response.json().get('data', []))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Pune')
