from MyFrameWork.myFrame.MyORM import MyModel, StringField, IntegerField, TextField


class Category(MyModel):
    __tablename__ = "category"
    __database__ = "myblog"
    id = IntegerField(primary_key=True, col_type="int(20)")
    name = StringField(col_type="varchar(10)")
    posts = StringField(col_type="varchar(255)", default="")


class Post(MyModel):
    __tablename__ = "post"
    __database__ = "myblog"
    id = IntegerField(primary_key=True, col_type="int(20)")
    content = TextField(col_type="text")
    category = IntegerField(col_type="int(20)", default=0)
    title = StringField(col_type="varchar(255)")

class User(MyModel):
    __tablename__ = "user"
    __database__ = "myblog"
    id=IntegerField(primary_key= True,col_type="int(20)")
    username = StringField(col_type="varchar(50)")
    pwd = StringField(col_type="varchar(60)")

