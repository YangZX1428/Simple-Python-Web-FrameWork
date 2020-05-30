from MyFrameWork.myFrame.MyApp import View, create_app, render_template, redirect, save_flash, url_for, session
from MyFrameWork.models import Category, Post, User
from faker import Faker
############################################################
#   用自己的框架实现的一个简单的博客应用，包括一些最基本的 #
#   登录和查看功能，没有实现注册和评论。                   #
############################################################

# 每次加载十篇文章
POST_PER_PAGE = 10


def get_post_num(c):
    posts = c["posts"]
    post_id_list = posts.split("|")
    return len(post_id_list) - 1


def global_value():
    category = Category.getAll()
    for c in category:
        c["posts"] = get_post_num(c)
    return {"category": category}


# 主页
class Index(View):
    def GET(self, request):
        posts = Post.getAll()[:10]
        category_name_list = []
        for post in posts:
            category_id = post["category"]
            category_name = Category.getById(category_id)["name"]
            category_name_list.append(category_name)
        return render_template("index.html", posts=posts, category_name_list=category_name_list)


# 文章主页
class post_page(View):
    def GET(self, request, **rule):
        post_id = rule.get("post_id", None)
        if post_id:
            post = Post.getById(post_id)
            category_name = Category.getById(post["category"]).get("name")
            return render_template("show_post.html", post=post, category_name=category_name)
        raise RuntimeError("Can't get post id !")


# 登录
class Login(View):
    def GET(self, request):
        return render_template("login.html")

    def POST(self, request):
        username = request.form.get("username", "")
        pwd = request.form.get("pwd", "")
        if username.strip() == "" or pwd.strip() == "":
            save_flash("输入不得为空!")
            return redirect(url_for("login"))
        try:
            user = User.getByFilter(username=username)
        except RuntimeError as e:
            save_flash("用户名不存在!")
            return redirect(url_for("login"))
        if user[0].get("pwd") != pwd:
            save_flash("密码错误!")
            return redirect(url_for("login"))
        else:
            session["username"] = username
            return redirect(url_for("index"))


# 登出
class Logout(View):
    def GET(self, request):
        if session["username"] is not None:
            session["username"] = None
        return redirect(request.args.get("next", "/index"))


# 分类页面
class Category_page(View):
    def GET(self, request, **rule):
        category_id = rule.get("category_id", None)
        category_obj = Category.getById(category_id)
        posts = Post.getByFilter(category=category_id)
        return render_template("category.html", category_obj=category_obj, posts=posts)


# 关于界面
class About(View):
    def GET(self, request):
        faker = Faker()
        return render_template("about.html", text=faker.text(2000))


# 获取更多
class get_more(View):
    def POST(self, request):
        # 获取页数
        page = int(request.form.get("page"))
        total_posts = Post.getAll()
        if 10 * (page - 1) > len(total_posts):
            return "None"
        if 10 * (page - 1) + 10 >= len(total_posts):
            posts = total_posts[10 * (page - 1):]
        else:
            posts = total_posts[10 * (page - 1):10 * (page - 1) + 10]
        category_name_list = []
        for p in posts:
            category = Category.getById(p.get("category"))
            category_name_list.append(category.get("name"))
        return render_template("_more.html", category_name_list=category_name_list, posts=posts)


# 定义路由表
urls = [{
    "url": "/index",
    "view": Index
},
    {
        "url": "/post/<int:post_id>",
        "view": post_page
    },
    {
        "url": "/login",
        "view": Login
    },
    {
        "url": "/logout",
        "view": Logout
    },
    {
        "url": "/category/<int:category_id>",
        "view": Category_page
    },
    {
        "url": "/about",
        "view": About
    },
    {
        "url": "/get_more",
        "view": get_more
    }
]

app = create_app()
app.add_url_rule(urls)
app.add_context_processsor(global_value())
