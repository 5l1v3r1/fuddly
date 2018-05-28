################################################################################
#
#  Copyright 2014-2016 Eric Lacombe <eric.lacombe@security-labs.org>
#
################################################################################
#
#  This file is part of fuddly.
#
#  fuddly is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  fuddly is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with fuddly. If not, see <http://www.gnu.org/licenses/>
#
################################################################################

import socket

from framework.plumbing import *
from framework.targets.debug import TestTarget
from framework.targets.network import NetworkTarget
from framework.knowledge.information import *
from framework.knowledge.feedback_handler import TestFbkHandler

project = Project()
project.default_dm = 'mydf'

logger = Logger(export_data=False, explicit_data_recording=False, export_orig=False,
                export_raw_data=True, enable_file_logging=False)

### KNOWLEDGE ###

project.add_knowledge(
    Hardware.X86_64,
    Language.C
)

project.register_feedback_handler(TestFbkHandler())

### TARGETS DEFINITION ###

class TutoNetTarget(NetworkTarget):

    def _custom_data_handling_before_emission(self, data_list):
        self.listen_to('localhost', 64001, 'Dynamic server interface')
        # self.connect_to('localhost', 64002, 'Dynamic client interface')
        # self._logger.collect_target_feedback('TEST', status_code=random.randint(-2,2))

    def _feedback_handling(self, fbk, ref):
        # self.remove_all_dynamic_interfaces()
        ok_status = 0
        return fbk, ok_status

tuto_tg = TutoNetTarget(host='localhost', port=12345, data_semantics='TG1', hold_connection=True)
tuto_tg.register_new_interface('localhost', 54321, (socket.AF_INET, socket.SOCK_STREAM), 'TG2',
                               server_mode=True, hold_connection=True)
tuto_tg.add_additional_feedback_interface('localhost', 7777, (socket.AF_INET, socket.SOCK_STREAM),
                                          fbk_id='My Feedback Source', server_mode=True)
tuto_tg.set_timeout(fbk_timeout=5, sending_delay=2)

net_tg = NetworkTarget(host='localhost', port=12345,
                       socket_type=(socket.AF_INET, socket.SOCK_STREAM),
                       hold_connection=True, server_mode=False)

udpnet_tg = NetworkTarget(host='localhost', port=12345,
                          socket_type=(socket.AF_INET, socket.SOCK_DGRAM),
                          hold_connection=True, server_mode=False)

udpnetsrv_tg = NetworkTarget(host='localhost', port=12345,
                          socket_type=(socket.AF_INET, socket.SOCK_DGRAM),
                          hold_connection=True, server_mode=True)

ETH_P_ALL = 3
rawnetsrv_tg = NetworkTarget(host='eth0', port=ETH_P_ALL,
                             socket_type=(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL)),
                             hold_connection=True, server_mode=False)
rawnetsrv_tg.register_new_interface(host='eth2', port=ETH_P_ALL,
                                    socket_type=(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL)),
                                    data_semantics='TG2')

### PROBE DEFINITION ###

@probe(project)
class P1(Probe):

    def start(self, dm, target, logger):
        self.cpt = 0

    def main(self, dm, target, logger):
        self.cpt += 1

        return ProbeStatus(self.cpt, info='This is a Linux OS!')


@probe(project)
class P2(Probe):

    def start(self, dm, target, logger):
        self.cpt = 10

    def main(self, dm, target, logger):
        self.cpt -= 1
        ps = ProbeStatus(self.cpt)
        ps.set_private_info('always KO!')
        return ps


@blocking_probe(project)
class health_check(Probe):

    def start(self, dm, target, logger):
        self.cpt = 0

    def stop(self, dm, target, logger):
        pass

    def main(self, dm, target, logger):
        self.cpt += 1

        status = 0
        if self.cpt > 10:
            status = -1

        return ProbeStatus(status)

serial_backend = Serial_Backend('/dev/ttyUSB0', username='test', password='test', slowness_factor=8)

@blocking_probe(project)
class probe_pid(ProbePID):
    backend = serial_backend
    process_name = 'bash'

@probe(project)
class probe_mem(ProbeMem):
    backend = serial_backend
    process_name = 'bash'
    tolerance = 1


### TARGETS ALLOCATION ###

targets = [(EmptyTarget(), (P1, 2), (P2, 1.4), health_check),
           tuto_tg, net_tg, udpnet_tg, udpnetsrv_tg, rawnetsrv_tg,
           (TestTarget(), probe_pid, (probe_mem, 0.2))]

### OPERATOR DEFINITION ###

@operator(project,
          args={'mode': ('strategy mode (0 or 1)', 0, int),
                'max_steps': ('maximum number of test cases', 10, int)})
class MyOp(Operator):

    def start(self, fmk_ops, dm, monitor, target, logger, user_input):
        monitor.set_probe_delay(P1, 1)
        monitor.set_probe_delay(P2, 0.2)
        if not monitor.is_probe_launched(P1) and self.mode == 0:
            monitor.start_probe(P1)
        if not monitor.is_probe_launched(P2) and self.mode == 0:
            monitor.start_probe(P2)

        self.cpt = 0
        self.detected_error = 0

        if self.mode == 1:
            fmk_ops.set_fuzz_delay(0)
        else:
            fmk_ops.set_fuzz_delay(0.5)

        return True

    def stop(self, fmk_ops, dm, monitor, target, logger):
        pass

    def plan_next_operation(self, fmk_ops, dm, monitor, target, logger, fmk_feedback):

        op = Operation()

        p1_ret = monitor.get_probe_status(P1).value
        p2_ret = monitor.get_probe_status(P2).value

        logger.print_console('*** status: p1: %d / p2: %d ***' % (p1_ret, p2_ret))

        if fmk_feedback.is_flag_set(FmkFeedback.NeedChange):
            change_list = fmk_feedback.get_flag_context(FmkFeedback.NeedChange)
            for dmaker, idx in change_list:
                logger.log_fmk_info('Exhausted data maker [#{:d}]: {:s} '
                                    '({:s})'.format(idx, dmaker['dmaker_type'],dmaker['dmaker_name']),
                                    nl_before=True, nl_after=False)
            op.set_flag(Operation.Stop)
            return op

        if p1_ret + p2_ret > 0:
            actions = [('SEPARATOR', UI(determinist=True)),
                       ('tSTRUCT', None, UI(deep=True)),
                       ('Cp', None, UI(idx=1)), ('Cp#1', None, UI(idx=3))]
        elif -5 < p1_ret + p2_ret <= 0:
            actions = ['SHAPE#specific', ('C#2', None, UI(path='.*prefix.$')), ('Cp#2', None, UI(idx=1))]
        else:
            actions = ['SHAPE#3', 'tTYPE#3']

        op.add_instruction(actions)

        if self.mode == 1:
            actions_sup = ['SEPARATOR#2', ('tSTRUCT#2', None, UI(deep=True)), ('SIZE', None, UI(sz=10))]
            op.add_instruction(actions_sup)

        self.cpt += 1

        return op


    def do_after_all(self, fmk_ops, dm, monitor, target, logger):
        linst = LastInstruction()

        if not monitor.is_target_ok():
            self.detected_error += 1
            linst.set_instruction(LastInstruction.RecordData)
            linst.set_operator_feedback('This input has crashed the target!')
            linst.set_operator_status(0)
        if self.cpt > self.max_steps and self.detected_error < 9:
            linst.set_operator_feedback("We have less than 9 data that trigger some problem with the target!"
                                        " You win!")
            linst.set_operator_status(-8)
        elif self.cpt > self.max_steps:
            linst.set_operator_feedback("Too many errors! ... You loose!")
            linst.set_operator_status(-self.detected_error)

        return linst
