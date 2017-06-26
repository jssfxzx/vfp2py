from __future__ import print_function

import os

import dbf


class DatabaseWorkspace(object):
    def __init__(self, tablename, alias=None):
        if alias:
            self.name = alias
        else:
            self.name = os.path.basename(os.path.splitext(tablename)[0]).lower()
        self.table = dbf.Table(tablename)
        self.table.open()
        if len(self.table) > 0:
            self.table.goto(0)


class DatabaseContext(object):
    def __init__(self):
        self.open_tables = [None]*10
        self.current_table = 0

    def _table_index(self, tablename=None):
        if not tablename:
            ind = self.current_table
        elif isinstance(tablename, (int, float)):
            ind = tablename
        else:
            tablenames = [t.name if t else None for t in self.open_tables]
            if tablename in tablenames:
                ind = tablenames.index(tablename)
            else:
                raise Exception('Table is not currently open')
        return ind

    def _get_table_info(self, tablename=None):
        return self.open_tables[self._table_index(tablename)]

    def create_table(self, tablename, setup_string, free):
        if free == 'free':
            dbf.Table(tablename, setup_string)
            self.use(tablename, 0, 'shared')

    def select(self, tablename):
        self.current_table = self._table_index(tablename)

    def use(self, tablename, workarea, opentype):
        if tablename is None:
            if workarea is 0:
                return
            self.open_tables[self._table_index(workarea)] = None
            return
        if workarea == 0:
            workarea = self.open_tables.index(None)
        self.open_tables[workarea] = DatabaseWorkspace(tablename)

    def used(self, tablename):
        try:
            self._table_index(tablename)
            return True
        except:
            return False

    def append(self, tablename, editwindow):
        table_info = self._get_table_info(tablename)
        table_info.table.append()
        self.goto(tablename, -1)

    def append_from(self, tablename, from_source, from_type='dbf'):
        table = self._get_table_info(tablename).table
        if from_type == 'dbf':
            with dbf.Table(from_source) as from_table:
                for record in from_table:
                    table.append(record)

    def replace(self, field, value, scope):
        field = field.lower().split('.')
        if len(field) > 1:
            if len(field) == 2:
                table = str(field[0])
            else:
                table = '.'.join(field[:-1])
            field = field[-1]
        else:
            field = field[0]
            table = None
        record = self._get_table_info(table).current_record
        dbf.write(record, **{field: value})

    def insert(self, tablename, values):
        table_info = self._get_table_info(tablename)
        table = table_info.table
        if isinstance(values, Array):
            for i in range(1,values.alen(1)+1):
                table.append(tuple(values[i, j] for j in range(1,values.alen(2)+1)))
        else:
            if isinstance(values, Custom):
                values = {field: getattr(values, field) for field in table.field_names if hasattr(values, field)}
            elif values is None:
                local = inspect.stack()[1][0].f_locals
                scope = variable.current_scope()
                values = {field: scope[field] for field in table.field_names if field in scope}
                values.update({field: local[field] for field in table.field_names if field in local})
            table.append(values)
        self.goto(tablename, -1)

    def skip(self, tablename, skipnum):
        try:
            self._get_table_info(tablename).table.skip(skipnum)
        except dbf.Eof:
            pass

    def goto(self, tablename, num):
        table = self._get_table_info(tablename).table
        if num == -1:
            table.bottom()
        else:
            num = num - 1
            table.goto(num)

    def delete_record(self, tablename, scope, num, for_cond=None, while_cond=None, recall=False):
        save_current_table = self.current_table
        self.select(tablename)
        if not for_cond:
            for_cond = lambda: True
        if not while_cond:
            while_cond = lambda: True
        table = self._get_table_info().table
        if scope.lower() == 'rest':
            condition = lambda table: not table.eof
        else:
            recno = self.recno()
            condition = lambda table: not table.eof and dbf.recno(table.current_record) - recno < num
        while condition(table) and while_cond():
            if for_cond():
                (dbf.undelete if recall else dbf.delete)(table.current_record)
            self.skip(None, 1)
        self.current_table = save_current_table

    def pack(self, pack, tablename, workarea):
        if tablename:
            table = dbf.Table(tablename)
            table.open()
            table.pack()
            table.close()
        else:
            self._get_table_info(workarea).table.pack()

    def reindex(self, compact_flag):
        self._get_table_info().table.reindex()

    def index_on(self, field, indexname, order, tag_flag, compact_flag, unique_flag):
        pass

    def close_tables(self, all_flag):
        self.open_tables = [None] * 10

    def recno(self):
        try:
            return dbf.recno(self.open_tables[self.current_table].table.current_record)
        except:
            return 0

    def reccount(self):
        try:
            return len(self.open_tables[self.current_table].table)
        except:
            return 0

    def recsize(self, workarea=None):
        return self._get_table_info(workarea).table.record_length

    def bof(self, workarea=None):
        return self._get_table_info(workarea).table.bof

    def eof(self, workarea=None):
        return self._get_table_info(workarea).table.eof

    def deleted(self, workarea=None):
        return dbf.is_deleted(self._get_table_info(workarea).table.current_record)

    def browse(self):
        table_info = self._get_table_info()
        table = table_info.table
        print('Tablename:', table_info.name)
        print(table.field_names)
        for record in table:
            print('->' if record is table.current_record else '  ', record[:])
