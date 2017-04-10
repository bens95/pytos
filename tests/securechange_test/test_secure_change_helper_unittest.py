#!/opt/tufin/securitysuite/ps/python/bin/python3.4

import time
import types

test_data_dir = "/opt/tufin/securitysuite/ps/tests/bin/Secure_Change_Test/"
from pytos.securechange.xml_objects.restapi.Step.AccessRequest.Verifier import AccessRequestVerifierResult
from pytos.common.definitions import XML_Tags
from pytos.securechange.helpers import Secure_Change_Helper
from pytos.securechange.xml_objects.rest import Ticket, Ticket_History_Activities, User, User_List, TicketList
from pytos.common.functions.Config import Secure_Config_Parser
from pytos.common.exceptions import REST_Bad_Request_Error
from pytos.common.logging.Logger import setup_loggers
import unittest

conf = Secure_Config_Parser()
LOGGER = setup_loggers(conf.dict("log_levels"), log_dir_path="/var/log/ps/tests")

# setting global variables that going to be used in the unittest suit
added_ticket_id = 0
canceled_ticked_id = 0
access_request_ticket_id = 1


class Test_Secure_Change_Helper(unittest.TestCase):
    def setUp(self):
        try:
            self.helper = Secure_Change_Helper.from_secure_config_parser(conf)
        except KeyError:
            self.helper = Secure_Change_Helper.from_secure_config_parser(conf)

    def test_01_post_ticket(self):
        global added_ticket_id
        ticket_obj = self.helper.read_ticket_template(test_data_dir + 'new_ticket.xml')
        # set the requester to user name 'a'
        user = 'a'
        ticket_obj.requester = user
        added_ticket_id = self.helper.post_ticket(ticket_obj)
        self.assertIsInstance(int, added_ticket_id)

    def test_02_get_ticket(self):
        # assert valid request
        ticket_id = added_ticket_id
        ticket = self.helper.get_ticket_by_id(ticket_id)
        self.assertIsInstance(ticket, Ticket)
        self.assertEqual(int(ticket.id), ticket_id)

        # assert invalid request
        with self.assertRaises(ValueError):
            self.helper.get_ticket_by_id(124381212)

    def test_03_redo_step(self):

        ticket_id = added_ticket_id

        ticket = self.helper.get_ticket_by_id(ticket_id)
        from_task = ticket.get_current_task()
        try:
            to_step_id = ticket.get_previous_step().id
        except IndexError:
            from_task.mark_as_done()
            self.helper.put_task(from_task)
            ticket = self.helper.get_ticket_by_id(ticket_id)
            from_task = ticket.get_current_task()
            to_step_id = ticket.get_previous_step().id

        self.helper.redo_step(from_task, to_step_id,
                              'redoing task with ID {} to step ID {}'.format(from_task.id, to_step_id))

        time.sleep(2)
        # Re-fetching ticket from database
        ticket = self.helper.get_ticket_by_id(ticket_id)
        self.assertEqual(ticket.get_current_task().id, to_step_id)

    def test_04_get_ticket_history_by_id(self):

        ticket_id = added_ticket_id
        ticket_history = self.helper.get_ticket_history_by_id(ticket_id)
        self.assertIsInstance(ticket_history, Ticket_History_Activities)
        self.assertEqual(int(ticket_history.ticket_id), ticket_id)

        with self.assertRaises(ValueError):
            self.helper.get_ticket_history_by_id(124381212)

    def test_06_reassign_task_by_username(self):

        ticket_obj = self.helper.read_ticket_template(test_data_dir  + 'new_ticket.xml')

        orig_user_name = 'a'
        reassigned_user_name = 'b'
        reassigned_user_id = 4

        ticket_obj.requester = orig_user_name

        ticket_id = self.helper.post_ticket(ticket_obj)

        ticket = self.helper.get_ticket_by_id(ticket_id)
        current_task = ticket.get_current_task()

        # in order to re-assign the card we must mark the current task as done
        current_task.mark_as_done()
        self.helper.put_task(current_task)
        # Re-fetching ticket from database.
        ticket = self.helper.get_ticket_by_id(ticket_id)
        current_task = ticket.get_current_task()

        self.helper.reassign_task_by_username(current_task, reassigned_user_name, "Cake!")
        # Re-fetching ticket from database.
        ticket = self.helper.get_ticket_by_id(ticket_id)
        current_task = ticket.get_current_task()
        self.assertEqual(current_task.assignee, reassigned_user_name)
        self.assertEqual(int(current_task.assignee_id), reassigned_user_id)

    def test_07_change_requester(self):

        # generate the ticket obj
        ticket = self.helper.get_ticket_by_id(added_ticket_id)

        # set new Requester as user id 5 named 'c'
        user_id = 5
        user_name = 'c'
        # assert that the original requeter is not the new one
        self.assertNotEqual(ticket.requester_id, user_id)
        comment = "Requester was modified from {} to {}".format(ticket.requester, user_name)

        # assert valid request
        self.helper.change_requester(added_ticket_id, user_id, comment)
        updated_ticket = self.helper.get_ticket_by_id(added_ticket_id)
        self.assertEqual(int(updated_ticket.requester_id), user_id)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.change_requester(added_ticket_id, 123, comment)

    def test_08_cancel_ticket_with_requester(self):

        global canceled_ticked_id
        #  creating a new ticket from template
        ticket_obj = self.helper.read_ticket_template(test_data_dir  + 'new_ticket.xml')
        user_name = 'a'
        user_id = 3
        ticket_obj.requester = user_name
        ticket_id = self.helper.post_ticket(ticket_obj)

        # assert valid request
        self.helper.cancel_ticket(ticket_id, user_id)
        ticket = self.helper.get_ticket_by_id(ticket_id)
        self.assertEqual("Ticket Cancelled", ticket.status)
        canceled_ticked_id = ticket_id

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.cancel_ticket(55555, user_id)

    def test_09_cancel_ticket_without_requester(self):

        #  creating a new ticket from template
        ticket_obj = self.helper.read_ticket_template(test_data_dir  + 'new_ticket.xml')
        user_name = 'a'
        ticket_obj.requester = user_name
        ticket_id = self.helper.post_ticket(ticket_obj)

        # assert valid request
        self.helper.cancel_ticket(ticket_id)
        ticket = self.helper.get_ticket_by_id(ticket_id)
        self.assertEqual("Ticket Cancelled", ticket.status)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.cancel_ticket(5555)

    def test_10_put_task(self):

        # Generate the ticket obj
        ticket = self.helper.get_ticket_by_id(added_ticket_id)
        # Getting the time value from the last task
        last_task = ticket.get_last_task()
        time_field = last_task.get_field_list_by_type(XML_Tags.Attributes.FIELD_TYPE_TIME)[0]
        time_field.set_field_value("15:15")

        # assert valid request
        self.helper.put_task(last_task)
        ticket = self.helper.get_ticket_by_id(added_ticket_id)
        last_task = ticket.get_last_task()
        time_field = last_task.get_field_list_by_type(XML_Tags.Attributes.FIELD_TYPE_TIME)[0]
        new_time = time_field.get_field_value()
        self.assertEqual("15:15", new_time)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.put_task("wrong value")

    def test_11_put_field(self):

        # Generate the ticket obj
        ticket = self.helper.get_ticket_by_id(added_ticket_id)
        # Getting the time value from the last task
        last_task = ticket.get_last_task()
        time_field = last_task.get_field_list_by_type(XML_Tags.Attributes.FIELD_TYPE_TIME)[0]
        time_field.set_field_value("20:20")

        # assert valid request
        result = self.helper.put_field(time_field)
        ticket = self.helper.get_ticket_by_id(added_ticket_id)
        last_task = ticket.get_last_task()
        time_field = last_task.get_field_list_by_type(XML_Tags.Attributes.FIELD_TYPE_TIME)[0]
        new_time = time_field.get_field_value()
        self.assertTrue(result)
        self.assertEqual("20:20", new_time)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.put_field("wrong value")

    def test_13_get_sc_user_by_id(self):
        # user 'a'
        user_id = 3

        # assert valid request
        user = self.helper.get_sc_user_by_id(user_id)
        self.assertIsInstance(user, User)
        self.assertEqual("a", user.name)
        self.assertEqual(int(user.id), 3)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.get_sc_user_by_id(123)

    def test_14_get_user_by_username(self):

        user_name = "a"
        # assert valid request
        user = self.helper.get_user_by_username(user_name)
        self.assertIsInstance(user, User)
        self.assertEqual("a", user.name)
        self.assertEqual(int(user.id), 3)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.get_user_by_username("Alfred")

    def test_17_get_ticket_ids_by_workflow_name(self):
        # assert valid request
        workflow_name = "My workflow"
        ticket_ids = self.helper.get_ticket_ids_by_workflow_name(workflow_name)

        self.assertIsInstance(ticket_ids, list)
        self.assertTrue(added_ticket_id in ticket_ids)

        # assert invalid request
        ticket_ids = self.helper.get_ticket_ids_by_workflow_name("NonExistsWorkflow")
        self.assertFalse(ticket_ids)

    def test_18_get_ticket_ids_by_status(self):

        status = "In Progress&desc=True"
        # assert valid request
        tickets = self.helper.get_ticket_ids_by_status(status)
        self.assertIsInstance(tickets, TicketList)
        # check that the ticket id  that was created in the tests is indeed inside the list the API returns
        ticket_found_in_list = False
        for ticket in tickets:
            if int(ticket.id) == added_ticket_id:
                ticket_found_in_list = True
        self.assertTrue(ticket_found_in_list)

        # assert invalid requests
        with self.assertRaises(REST_Bad_Request_Error):
            self.helper.get_ticket_ids_by_status("Not Exsisting Status")

    def test_21_render_template_for_ticket(self):

        ticket = self.helper.get_ticket_by_id(canceled_ticked_id)
        # need to send first arg template type Enum
        template = self.helper.render_template_for_ticket("ACTIVITY_TICKET_CANCEL", ticket)

        self.assertIsInstance(template, tuple)

    def test_22_get_ticket_link(self):

        link = self.helper.get_ticket_link(added_ticket_id)
        self.assertTrue("securechangeworkflow/pages/myRequest/myRequestsMain.seam?ticketId={}".format(added_ticket_id)
                        in link)

    def test_22_get_ticket_link_task(self):

        ticket = self.helper.get_ticket_by_id(added_ticket_id)
        last_task = ticket.get_last_task()
        link = self.helper.get_ticket_link(added_ticket_id, last_task.id)
        self.assertTrue("securechangeworkflow/pages/myRequest/myRequestsMain.seam?ticketId={}&taskid={}".format(
            added_ticket_id, last_task.id) in link)

    def test_24_get_user_by_email(self):
        user_name = 'a'
        email = "test@tufin.com"

        # assert valid request
        users = self.helper.get_user_by_email(email)
        self.assertIsInstance(users, User_List)
        # get all user name and check if user a in the list
        user_names = [user.name for user in users]
        self.assertTrue(user_name in user_names)

        # assert invalid request
        users = self.helper.get_user_by_email("NotExistEmail@tufin.com")
        self.assertFalse(users)

    def test_25_get_sc_user_by_email(self):
        user_name = 'a'
        email = "test@tufin.com"

        # assert valid request
        user = self.helper.get_sc_user_by_email(email)
        self.assertIsInstance(user, User)
        self.assertEqual(user_name, user.name)

        # assert invalid requests
        with self.assertRaises(ValueError):
            self.helper.get_sc_user_by_email("notrealemail@tufin.com")

    def test_26_get_all_members_of_group(self):
        group_name = "Tufin"
        user_names = ["a", "b", "c"]

        # assert valid request
        members = self.helper.get_all_members_of_group(group_name)
        members_names = [member.name for member in members]
        for user in user_names:
            self.assertTrue(user in members_names)

        # assert invalid request
        with self.assertRaises(ValueError):
            self.helper.get_all_members_of_group("a")

    def test_27_get_all_members_of_group_by_group_id(self):

        group_id = 6
        user_names = ["a", "b", "c"]

        # assert valid request
        members = self.helper.get_all_members_of_group_by_group_id(group_id)
        members_names = [member.name for member in members]
        for user in user_names:
            self.assertTrue(user in members_names)

        # assert invalid request
        with self.assertRaises(ValueError):
            self.helper.get_all_members_of_group_by_group_id(3)

    def test_29_get_verifier_results(self):

        # global variable
        ticket_id = access_request_ticket_id

        ticket = self.helper.get_ticket_by_id(ticket_id)
        last_task = ticket.get_last_task()
        last_step = ticket.get_last_step()
        ar_field = last_task.get_field_list_by_type(XML_Tags.Attributes.FIELD_TYPE_MULTI_ACCESS_REQUEST)[0]
        # create a list of access request id's for calling the get_verifier_results API
        ar_ids = [ar.id for ar in ar_field.access_requests]

        # assert the values of each result - These are valid requests
        for verifier, ar_id in zip(ar_field.get_all_verifier_results(), ar_ids):
            # assert the first 2 access request that we know they have verifier results
            if ar_ids.index(ar_id) in [0, 1]:
                verifier_result = self.helper.get_verifier_results(ticket_id, last_step.id, last_task.id, ar_id)
                self.assertIsInstance(verifier_result, AccessRequestVerifierResult)
                if ar_ids.index(ar_id) == 0:
                    # assert that the first AR is not implemented as excpected
                    self.assertTrue(verifier.is_not_implemented())
                else:
                    # assert that the first AR is implemented as excpected
                    self.assertTrue(verifier.is_implemented())
            # assert that the third AR is not available as excpected
            elif ar_ids.index(ar_id) == 2:
                try:
                    self.helper.get_verifier_results(ticket_id, last_step.id, last_task.id, ar_id)
                except ValueError as value_error:
                    self.assertIsInstance(value_error, ValueError)
                    self.assertTrue(verifier.is_not_available())

    def test_31_get_ticket_ids_with_expiration_date(self):

        ticket_found = False
        tickets = self.helper.get_ticket_ids_with_expiration_date()
        for ticket in tickets:
            if access_request_ticket_id == ticket:
                ticket_found = True

        self.assertIsInstance(tickets, types.GeneratorType)
        self.assertTrue(ticket_found)


if __name__ == '__main__':
    unittest.main()