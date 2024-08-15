# from .gallery import gallery_routes_bp
# from .thumb import thumb_routes_bp
# from .user import user_routes_bp
from .accounts import account_routes_bp
# from .merge_video import merge_video_routes_bp


def register_apis_routes(app):
    app.register_blueprint(account_routes_bp, url_prefix="/api/v1/account")
    # app.register_blueprint(merge_video_routes_bp, url_prefix="/api/v1/merge/video")
    # app.register_blueprint(thumb_routes_bp, url_prefix="/api/v1/thumb")
    # app.register_blueprint(user_routes_bp, url_prefix="/api/v1/user")
    # app.register_blueprint(gallery_routes_bp, url_prefix="/api/v1/gallery")

    return app
