from werkzeug.wrappers import Response, Request
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, MethodNotAllowed, \
    NotImplemented, NotFound
from werkzeug.serving import run_simple
import os
from jinja2 import Environment, FileSystemLoader
import json
from werkzeug.wsgi import SharedDataMiddleware

################################################################################
#    用werkzeug实现的一个简单web框架                                           #
#    功能包括简单的路由，模板渲染，重定向，闪现消息，简单的会话功能以及ORM支持 #
################################################################################



# 全局保存url映射信息
url_map = Map()
# 保存模板全局变量
context_processor = {}
# 保存请求
global_request = None
# 保存session
session = {"_flash": []}


class View(object):
    # 请求方式与处理函数对应
    def __init__(self):
        self.methods = {
            'GET': self.GET,
            'POST': self.POST
        }

    # 定义两种基本请求方式
    # 视图类可覆盖请求方式进行不同处理
    def GET(self, request):
        raise MethodNotAllowed()

    def POST(self, request):
        raise MethodNotAllowed()

    # 请求调度
    def dispatch_request(self, request, *args, **options):
        # 保存request对象至全局变量中
        global global_request
        global_request = request
        # 判断请求类型并将请求分发给相应的处理函数，返回该函数
        if request.method in self.methods:
            return self.methods[request.method](request, *args, **options)
        else:
            return '<h1>Unknown or unsupported require method</h1>'

    # 闭包，将视图函数类本身发送给请求调度函数，获取对应的视图函数并返回
    @classmethod
    def get_func(cls):
        def func(*args, **kwargs):
            obj = func.view_class()
            return obj.dispatch_request(*args, **kwargs)

        func.view_class = cls
        return func


class App(object):

    def __init__(self):
        # url和视端点的映射字典
        # 端点和视图函数的映射
        self.view_func = {}
        self.url_map = Map()

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        try:
            # 构造request对象
            request = Request(environ)
            # 获取url适配器
            adapter = self.url_map.bind_to_environ(request.environ)
            # 获取端点值以及动态参数部分
            endpoint, values = adapter.match()
            # 保存端点值以便获取
            request.endpoint = endpoint
            # 获取端点对应的视图函数
            view = self.view_func.get(endpoint, None)
            if view:
                # 将请求和url动态部分发送给视图函数获得响应对象
                response = view(request, **values)
                # 当视图函数返回重定向请求时不再包装成Response对象，直接返回
                if response.__class__ != Response:
                    response = Response(response, content_type='text/html;charset=UTF-8')
            else:
                response = Response('<h1>404 Not Found<h1>', content_type='text/html; charset=UTF-8')
                response.status_code = 404
        except HTTPException as e:
            response = e
        # 返回响应
        return response(environ, start_response)

    def add_context_processsor(self, values):
        """
        添加全局变量
        :param values:{...}
        :return: None
        """
        global context_processor
        context_processor = values

    # 添加路由规则
    def add_url_rule(self, urls):
        """
        添加路由规则
        :param urls:一个列表，其中每一个项为一个字典，键为url和view，表示路径和对应的视图函数类
        :return: None
        """
        global url_map
        for url in urls:
            # 路由url与相应的端点组成键值对
            # 默认端点为该视图函数类的类名小写形式
            rule = Rule(url["url"], endpoint=url["view"].__name__.lower())
            self.url_map.add(rule)
            self.view_func[url['view'].__name__.lower()] = url['view'].get_func()
        url_map = self.url_map

    # 默认在本地5000端口上运行
    def run(self, port=5000, ip='127.0.0.1', debug=False):
        run_simple(ip, port, self, use_debugger=debug, use_reloader=True)


def url_for(endpoint, server_name="127.0.0.1:5000", external=False, filename=None, **values):
    """
    返回端点值对应的url
    :param endpoint: 端点值(会自动转化为小写)
    :param server_name: App实例程序所在的服务器ip
    :param values: url动态参数部分
    :param external: 生成绝对url
    :param filename : static资源的路径
    :return: 对应的url
    """
    # filename不为空时返回静态资源路径
    if filename is not None:
        file_path = os.path.join('\%s'%endpoint, filename)
        return file_path
    # 绑定服务器地址
    urls = url_map.bind(server_name)
    # 通过端点获取对应的url
    relative_url = urls.build(endpoint.lower(), values, force_external=external)
    return relative_url


# 模板支持，模板文件夹默认路径为当前app实例同级的templates文件夹
def render_template(template, **ctx):
    """
    :param template: html文件名
    :param ctx: 要传入html 的参数
    :return: html标签代码
    """
    # 定位template文件夹的路径
    global context_processor, global_request
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    # 在渲染模板时将一些辅助函数和全局变量传入以便在html代码中使用
    ctx["url_for"] = url_for
    ctx["request"] = global_request
    ctx["session"] = session
    ctx["get_flash"] = get_flash
    # 将render_template 方法中的键值对参数加入渲染参数列表中
    for k, v in context_processor.items():
        ctx[k] = v
    # 创建jinja环境
    jinja_env = Environment(loader=FileSystemLoader(path), autoescape=True)
    t = jinja_env.get_template(template)
    return t.render(ctx)


def jsonify(**values):
    """
    返回json格式的响应数据
    :param values: 接收键值对
    :return: json格式的response
    """
    json_data = json.dumps(values)
    response = Response(json_data, content_type="application/json;charset=UTF-8")
    return response


def save_flash(msg):
    """
    模拟flash的功能，使用session中的_flash键保存消息列表
    :param msg: 消息
    :return: None
    """
    session["_flash"].append(msg)


def get_flash():
    """
    删除并返回flash列表中的最后一个元素
    :return: String
    """
    if len(session["_flash"]) > 0:
        return session["_flash"].pop()
    return None


def create_app(with_static=True):
    """
    创建app对象，加入了中间件
    :param with_static:是否开启访问静态资源模式
    :return: app对象
    """
    app = App()
    if with_static:
        # 模板中可使用static中的资源
        # <link rel=stylesheet href=/static/style.css type=text/css>
        app.wsgi_app = SharedDataMiddleware(
            app.wsgi_app, {"/static": os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")}
        )
    return app


from werkzeug.utils import redirect
