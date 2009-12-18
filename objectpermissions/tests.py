from django.test import TestCase
from django.test.client import Client
from django.contrib.flatpages.models import FlatPage
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
# Test against flat pages

import objectpermissions
from models import ModelPermissions, UserPermission, GroupPermission

class TestModelPermissions(TestCase):
    perms = ['Perm1', 'Perm2', 'Perm3', 'Perm4']
    values = [1,2,4,8]

    def testObjectCapabilities(self):
        mp = ModelPermissions(self.perms)
        
        self.assertEquals(mp.Perm1, 1)
        self.assertEquals(mp.Perm2, 2)
        self.assertEquals(mp.Perm3, 4)
        self.assertEquals(mp.Perm4, 8)
    
    def testDictCapabilities(self):
        mp = ModelPermissions(self.perms)
        
        self.assertEquals(mp['Perm1'], 1)
        self.assertEquals(mp['Perm2'], 2)
        self.assertEquals(mp['Perm3'], 4)
        self.assertEquals(mp['Perm4'], 8)
        
        self.assertTrue('Perm3' in mp)
        self.assertFalse('Perm5' in mp)
        
        self.assertEquals(mp.keys(), self.perms)
        self.assertEquals(mp.values(), self.values)
    
    def testConversion(self):
        mp = ModelPermissions(self.perms)
        
        self.assertEquals(mp.as_int('Perm1'), 1)
        self.assertEquals(mp.as_int(['Perm1', 'Perm2', 'Perm4']), 1 | 2 | 8)
        self.assertEquals(mp.as_int(['Perm3', 'Perm2', 'Perm4']), 4 | 2 | 8)
        self.assertRaises(AttributeError, mp.as_int, ['Perm5', 'Perm2', 'Perm4'])

class TestRegistration(TestCase):
    perms = ['Perm1', 'Perm2', 'Perm3', 'Perm4']
    values = [1,2,4,8]
    
    def setUp(self):
        self.fp = FlatPage.objects.create(url='dummy/', title="dummy", enable_comments=False, registration_required=False)
        try:
            objectpermissions.register(FlatPage, self.perms)
        except objectpermissions.AlreadyRegistered:
            pass
        self.fp.save()
        
        self.u = User.objects.create_user('simple_guy','simple@guy.com', 'password')
        self.g = Group(name="simple_group")
        self.g.save()
        
    def testRegiser(self):
        self.assertTrue(hasattr(FlatPage, 'user_perms_set'))
        self.assertTrue(hasattr(FlatPage, 'group_perms_set'))
        self.assertTrue(hasattr(FlatPage, 'perms'))
    
    def testGrantUserPermissions(self):
        fp = self.fp
        u = self.u
        
        u.grant_object_perm(fp, fp.perms.Perm1)
        self.assertTrue(u.has_object_perm(fp, fp.perms.Perm1))
        self.assertFalse(u.has_object_perm(fp, fp.perms.Perm2))
        self.assertFalse(u.has_object_perm(fp, fp.perms.Perm3))
        self.assertTrue(u.has_object_perm(fp, [fp.perms.Perm1+fp.perms.Perm2]))
        self.assertTrue(u.has_any_object_perm(fp, [fp.perms.Perm1+fp.perms.Perm2]))
        self.assertFalse(u.has_all_object_perm(fp, [fp.perms.Perm1+fp.perms.Perm2]))
        
        
        up = UserPermission.objects.get(user=self.u)
        self.assertEquals(up.permission, fp.perms.Perm1)
        self.assertEquals(up.content_type, ContentType.objects.get_for_model(FlatPage))
        self.assertEquals(up.object_id, fp.id)
        
        self.assertEquals(fp.perms.as_string_list(13), ['Perm1', 'Perm3', 'Perm4'])
        self.assertEquals(fp.perms.as_int_list(13), [1,4,8])
        self.assertEquals(fp.perms.as_choices(13), [(1,'Perm1'),(4,'Perm3'),(8,'Perm4')])
        
        u.grant_object_perm(fp, [fp.perms.Perm2, fp.perms.Perm3])
        up = UserPermission.objects.get(user=self.u)
        self.assertEquals(up.content_type, ContentType.objects.get_for_model(FlatPage))
        self.assertEquals(up.object_id, fp.id)
        self.assertEquals(up.permission, fp.perms.Perm1 | fp.perms.Perm2 | fp.perms.Perm3)
    
    def testRevokeUserPermission(self):
        fp = self.fp
        u = self.u
        
        u.grant_object_perm(fp, fp.perms.Perm1)
        self.assertTrue(u.has_object_perm(fp, fp.perms.Perm1))
        
        u.revoke_object_perm(fp, fp.perms.Perm1)
        self.assertFalse(u.has_object_perm(fp, fp.perms.Perm1))
    
    
    def testGetUserPermissions(self):
        fp = self.fp
        u = self.u
        g = self.g
        g.user_set.add(u)
        
        # Clean the slate
        u.revoke_all_object_perm(fp)
        g.revoke_all_object_perm(fp)
        self.assertEquals(u.get_object_perm(fp), 0)
        self.assertEquals(g.get_object_perm(fp), 0)
        
        u.grant_object_perm(fp, fp.perms.Perm1 + fp.perms.Perm4)
        self.assertEquals(u.get_object_perm(fp), 9)
        self.assertEquals(u.get_object_perm_as_str_list(fp), ['Perm1', 'Perm4'])
        self.assertEquals(u.get_object_perm_as_int_list(fp), [1, 8])
        self.assertEquals(u.get_object_perm_as_choices(fp), [(1, 'Perm1'), (8,'Perm4')])
        
        # Test that the group permissions work correctly with the user perms
        g.grant_object_perm(fp, fp.perms.Perm1+fp.perms.Perm3)
        self.assertEquals(u.get_object_perm(fp), fp.perms.Perm1+fp.perms.Perm3+fp.perms.Perm4)
        
        # Revoking the Perm1 for the user, shouldn't change anything because
        # The group also has it
        u.revoke_object_perm(fp, fp.perms.Perm1)
        self.assertEquals(u.get_object_perm(fp), fp.perms.Perm1+fp.perms.Perm3+fp.perms.Perm4)
        
        g.revoke_object_perm(fp, fp.perms.Perm1)
        self.assertEquals(u.get_object_perm(fp), fp.perms.Perm3+fp.perms.Perm4)
    
    def testSignals(self):
        fp = self.fp
        u = self.u
        g = self.g
        g.user_set.add(u)
        
        # Clean the slate
        u.revoke_all_object_perm(fp)
        g.revoke_all_object_perm(fp)
        self.assertEquals(u.get_object_perm(fp), 0)
        self.assertEquals(g.get_object_perm(fp), 0)
        
        def my_user_handler(sender, **kwargs):
            self.assertTrue(isinstance(sender, UserPermission))
            self.assertEquals(kwargs['content_obj'], fp)
        
        def my_group_handler(sender, **kwargs):
            self.assertTrue(isinstance(sender, GroupPermission))
            self.assertEquals(kwargs['content_obj'], fp)
        
        from signals import permission_changed
        permission_changed.connect(my_user_handler)
        
        u.grant_object_perm(fp, fp.perms.Perm1)
        permission_changed.disconnect(my_user_handler)
        permission_changed.connect(my_group_handler)
        
        g.grant_object_perm(fp, fp.perms.Perm2)