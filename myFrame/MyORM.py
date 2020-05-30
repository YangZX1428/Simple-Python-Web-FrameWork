import pymysql
import os


# 返回由问号组成的占位符，以便后面替换
def create_args_string(n):
    string = ''
    for i in range(n):
        if i < n - 1:
            string += '?,'
        else:
            string += "?"
    return string


def toDict(cols, result):
    result_list = []
    for t in result:
        d = {}
        for k, v in zip(cols, t):
            d[k] = v
        result_list.append(d)
    return result_list


class Base:
    # 连接数据库相关变量
    def __init__(self, user, password, database, host='127.0.0.1', port=3306, charset='utf-8'):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.charset = charset
        self.con = pymysql.connect(host=self.host, port=self.port, user=self.user, passwd=self.password,
                                   db=self.database)

    # 执行相关sql语句
    def execute_sql(self, sql, params=None):
        cursor = self.con.cursor()
        rows = cursor.execute(sql, params)
        self.con.commit()
        results = cursor.fetchall()
        cursor.close()
        return rows, results


class Field(object):
    def __init__(self, name, col_type, primary_key, default):
        self.name = name
        self.col_type = col_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return "<%s,%s:%s>" % (self.__class__.__name__, self.name, self.col_type)


class StringField(Field):
    # 字符串字段，字段类型默认为varchar
    def __init__(self, name=None, col_type="varchar(100)", primary_key=False, default=None):
        super(StringField, self).__init__(name, col_type, primary_key, default)


class IntegerField(Field):
    def __init__(self, name=None, col_type="int(20)", primary_key=False, default=None):
        super(IntegerField, self).__init__(name, col_type, primary_key, default)


class TextField(Field):
    def __init__(self, name=None, col_type="text", primary_key=False, default=None):
        super(TextField, self).__init__(name, col_type, primary_key, default)


class ModelMetaClass(type):
    # 在构造方法前先调用
    def __new__(cls, name, bases, attrs):
        if name == "MyModel":
            return type.__new__(cls, name, bases, attrs)
        # 获取表名
        tablename = attrs.get('__tablename__', name)
        # 保存类属性和字段的映射关系
        mapping = dict()
        # 保存主键的属性名
        primary = None
        # 保存其他字段的属性名
        fields = []
        for k, v in attrs.items():
            if isinstance(v, Field):
                # 映射关系写入mapping
                mapping[k] = v
                # 设置主键
                if v.primary_key:
                    if primary:
                        raise RuntimeError(" Duplicate primary key in field %s" % k)
                    primary = k
                else:
                    # 非主键的添加到fields中
                    fields.append(k)
        if not primary:
            raise RuntimeError("No primary key found !")

        for k in mapping.keys():
            attrs.pop(k)
        repr_fields = ["`%s`" % f for f in fields]
        # 保存
        attrs["__mapping__"] = mapping
        attrs["__tablename__"] = tablename
        attrs["__fields__"] = fields
        attrs["__primary_key__"] = primary
        attrs["__select__"] = "select `%s`,%s from %s" % (primary, ','.join(repr_fields), tablename)
        attrs["__insert__"] = "insert into %s values(%s)" % (tablename, create_args_string(len(repr_fields) + 1))
        attrs["__delv__"] = "delete from %s where %s=" % (tablename, primary)
        attrs['db'] = Base(os.getenv("db_user"), os.getenv("db_password"), database=attrs['__database__'])
        # attrs['db'] = Base("root", "4343594.", database=attrs['__database__'])
        return type.__new__(cls, name, bases, attrs)


class MyModel(dict, metaclass=ModelMetaClass):
    def __init__(self, **kw):
        super(MyModel, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("%s object doesn't has attribute %s" % (self.__class__.__name__, key))

    def __setattr__(self, key, value):
        self[key] = value

    # 返回键对应的值，若该值不存在则设为默认值并返回
    def getValue(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.mapping[key]
            if field.default is not None:
                value = field.default
                setattr(self, key, value)
        return value

    # 插入操作
    def insert(self):
        """
        将调用该方法的对象作为一条记录加入相应的表中
        如
            obj = User(id=1,name='yzx')
            obj.insert()
        :return: 插入是否成功，成功则返回1
        """
        # 组成实参列表
        insert_values = [self.getValue(key) for key in self.__fields__]
        insert_values.insert(0, self.getValue(self.__primary_key__))
        # 将问号占位符替换成%s
        sql = self.__insert__.replace("?", "%s")
        # 执行插入语句
        rows, results = self.db.execute_sql(sql, insert_values)
        return rows

    @classmethod
    def setValue(cls, id, col, value):
        """
        更新数据库的值
        调用
            ClassName.setValue(id,col,value)
        :param id: id值
        :param col: 要更新的列名
        :param value: 要更新的目标值
        :return: 是否更新成功，成功返回1否则0
        """
        if type(value) == int:
            sql = "update %s set %s=%d where id=%d" % (cls.__tablename__, col, value, id)
        else:
            sql = "update %s set %s='%s' where id=%d" % (cls.__tablename__, col, value, id)
        rows, result = cls.db.execute_sql(sql)
        if not rows:
            raise RuntimeError("Can't find data where id = %d" % id)
        return rows

    @classmethod
    def delete(cls, id):
        """
        删除id为某个值的记录
        如
            ClassName.delete(id)
        :param id: id值
        :return: 是否更新成功，成功返回1否则0
        """
        sql = cls.__delv__ + str(id)
        rows, result = cls.db.execute_sql(sql)
        if not rows:
            raise RuntimeError("Can't find data where id = %d" % id)
        return rows

    @classmethod
    def create(cls):
        info = {}
        for k, v in cls.__mapping__.items():
            info[k] = [v.primary_key, v.col_type, v.default]
        sql = "create table " + cls.__tablename__ + "("
        primary = None
        for k, v in info.items():
            col_info = "%s %s not null" % (k, v[1])
            if v[0]:
                primary = k
            if v[2] is not None:
                col_info += " default '%s'" % v[2] if type(v[2]) == str else " default %d" % v[2]
            sql += col_info + ","
        sql += "primary key(`%s`))engine=innodb default charset=utf8;" % primary
        rows, result = cls.db.execute_sql(sql)
        if not rows:
            print("Create table `%s` (in database `%s`) success!" % (cls.__tablename__, cls.__database__))

    @classmethod
    def getAll(cls):
        """
        获取某个表的所有数据
        返回数据格式为一个列表
        列表的每一项为字典，键为列名。
        :return:list
        """
        rows, result = cls.db.execute_sql(cls.__select__)
        cols = [cls.__primary_key__] + cls.__fields__
        return toDict(cols, result)

    @classmethod
    def getById(cls, id):
        """
        根据id获取相应记录
        :param id:
        :return: dict
        """
        sql = cls.__select__ + " where id=%d" % id
        rows, result = cls.db.execute_sql(sql)
        cols = [cls.__primary_key__] + cls.__fields__
        if result == ():
            raise RuntimeError("Can't find data that matches id = %d !" % id)
        return toDict(cols, result)[0]

    @classmethod
    def getByFilter(cls, **filter):
        """
        根据过滤器获取记录
        如
            ClassName.getByFilter(name='yzx')
        :param filter: 过滤条件
        :return: list
        """
        if len(filter) > 1:
            raise RuntimeError("filter can receive only 1 argument but %d was given" % len(filter))
        sql = ""
        col = ""
        value = ""
        for k, v in filter.items():
            col = k
            if type(v) == int:
                value = str(v)
                sql = "select * from %s where %s=%d" % (cls.__tablename__, k, v)
            else:
                value = v
                sql = "select * from %s where %s='%s'" % (cls.__tablename__, k, v)
        rows, result = cls.db.execute_sql(sql)
        cols = [cls.__primary_key__] + cls.__fields__
        if not rows:
            raise RuntimeError("Can't find data that matches %s = %s !" % (col, value))
        return toDict(cols, result)

    @classmethod
    def create_all(cls):
        """
        创建所有数据表类
        :return: None
        """
        for table in cls.__subclasses__():
            table.create()
