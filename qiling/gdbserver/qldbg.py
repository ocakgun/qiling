from qiling.gdbserver.reg_table import *


class Qldbg(object):
    def __init__(self):
        self.arch = None
        self.mode = None
        self.current_address = 0x0
        self.current_address_size = 0x0
        self.last_bp = 0x0
        self.ql = None
        self.entry_point = None
        self.exit_point = None
        self.soft_bp = False
        self.has_soft_bp = False

        self.bp_list = []
        self.mapping = []
        self.entry_context = {}
        self.breakpoint_count = 0x0
        self.skip_bp_count = 0x0

    def initialize(self, ql, exit_point=None, mappings=None):
        self.ql = ql
        self.current_address = self.entry_point = self.ql.entry_point
        self.exit_point = exit_point
        self.mapping = mappings
        self.ql.hook_code(self.dbg_hook)

    def dbg_hook(self, ql, address, size):
        """
        Modified this function for qiling.gdbserver by kabeor from https://github.com/iGio90/uDdbg
        """
        try:
            self.mapping.append([hex(address), size])
            self.current_address = address

            hit_soft_bp = False

            if self.soft_bp:
                self.soft_bp = False
                hit_soft_bp = True

            if address != self.last_bp and address in self.bp_list or self.has_soft_bp:
                if self.skip_bp_count > 0:
                    self.skip_bp_count -= 1
                else:
                    self.breakpoint_count += 1
                    ql.stop()

                    self.last_bp = address
                    self.ql.dprint('breakpoint: ', hex(address))
            elif address == self.last_bp:
                self.last_bp = 0
            self.has_soft_bp = hit_soft_bp
            if self.current_address + size == self.exit_point:
                print('emulation finished success !!!')
        except KeyboardInterrupt as ex:
            print(">>> paused at 0x%x, instruction size = %u" % (address, size))
            ql.stop()

    def bp_insert(self, add):
        if add not in self.bp_list:
            self.bp_list.append(add)
            self.ql.dprint('bp added at: ', hex(add))

    def bp_remove(self, type, addr, len):
        self.bp_list.remove(addr)
        self.ql.dprint('bp remove: ', hex(addr))

    def resume_emu(self, address=None, skip_bp=0):
        """
        Modified this function for qiling.gdbserver by kabeor from https://github.com/iGio90/uDdbg
        """
        if address is not None:
            self.current_address = address

        self.skip_bp_count = skip_bp
        if self.exit_point is not None:
            self.ql.dprint('emu restart at:  ', hex(self.current_address))

            if len(self.entry_context) == 0:
                self.entry_context = {
                    'memory': {},
                    'regs': {}
                }
                map_list = self.mapping
                for maps in map_list:
                    map_address = int(maps[0], 16)
                    map_len = maps[1]
                    self.entry_context['memory'][map_address] = bytes(self.ql.uc.mem_read(map_address, map_len))

                for r in arch_reg[self.ql.arch]:
                    try:
                        self.entry_context['regs'][r] = self.ql.uc.reg_read(r)
                    except Exception as ex:
                        pass
            start_addr = self.current_address
            self.ql.uc.emu_start(start_addr, self.exit_point)
