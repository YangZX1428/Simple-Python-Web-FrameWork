from faker import Faker
from MyFrameWork.models import Post, Category
from random import randint

faker = Faker()


# generate fake categories

def fake_category(count=10):
    for i in range(count):
        c = Category(id=i + 1, name=faker.word(), posts="")
        c.insert()


# generate fake posts
def fake_posts(count=30):
    for i in range(count):
        c = randint(1, len(Category.getAll()))
        p = Post(id=i + 1, content=faker.text(2000), category=c, title=faker.sentence())
        p.insert()

def fun():
    for p in Post.getAll():
        c = Category().getById(p["category"])
        posts = c[0]["posts"]
        new_posts = posts+"|%d"%p["id"]
        Category.setValue(p["category"],"posts",new_posts)
fake_posts()
