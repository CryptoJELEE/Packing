"""
Flask 애플리케이션 팩토리
"""
from flask import Flask
from config.settings import Config

def create_app(config_class=Config):
    """Flask 앱 생성"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # 라우트 등록 (나중에 분리할 때 사용)
    # from app.routes import master, order, simulation, visualization
    # app.register_blueprint(master.bp)
    # app.register_blueprint(order.bp)
    # app.register_blueprint(simulation.bp)
    # app.register_blueprint(visualization.bp)
    
    return app

