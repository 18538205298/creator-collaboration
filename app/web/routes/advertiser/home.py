from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.domain.advertiser.recommender_service import AdvertiserRecommenderService
# ... 其他导入 ...

# 初始化蓝图
advertiser_home_bp = Blueprint('advertiser', __name__, url_prefix='/advertiser/home')

# 初始化推荐服务
recommender_service = AdvertiserRecommenderService()

# ... 其他路由函数 ...

@advertiser_home_bp.route('/recommended')
def home_recommended():
    """广告主首页 - 推荐合作者页面"""
    advertiser_id = session.get('user_id')
    if not advertiser_id:
        advertiser_id = 101  # 默认使用ID为101的广告主进行测试
    
    # 使用推荐服务获取推荐合作者
    try:
        trending_collaborators = recommender_service.get_trending_collaborators(limit=3)
        print(f"获取到 {len(trending_collaborators) if trending_collaborators else 0} 个热门合作者")
    except Exception as e:
        print(f"获取热门合作者出错: {str(e)}")
        trending_collaborators = []
    
    try:
        new_collaborators = recommender_service.get_new_rising_collaborators(limit=2)
        print(f"获取到 {len(new_collaborators) if new_collaborators else 0} 个新晋合作者")
    except Exception as e:
        print(f"获取新晋合作者出错: {str(e)}")
        new_collaborators = []
    
    # 自定义推荐合作者 - 基于广告主的特定需求
    try:
        recommended_collaborators = recommender_service.get_recommended_collaborators(advertiser_id, limit=5)
        print(f"获取到 {len(recommended_collaborators) if recommended_collaborators else 0} 个推荐合作者")
    except Exception as e:
        print(f"获取推荐合作者出错: {str(e)}")
        recommended_collaborators = []
    
    # 如果没有获取到任何推荐数据，则提供一些模拟数据确保界面有内容显示
    if not trending_collaborators and not new_collaborators and not recommended_collaborators:
        print("所有推荐列表为空，使用模拟数据")
        # 模拟数据
        mock_collaborator = {
            'id': 1,
            'username': '测试合作者',
            'avatar_url': None,
            'followers_count': 25000,
            'likes_count': 100000,
            'content_domain': '测试领域',
            'content_style': '测试风格',
            'platform': '测试平台',
            'previous_collaboration_count': 5
        }
        recommended_collaborators = [mock_collaborator.copy() for _ in range(3)]
        trending_collaborators = [mock_collaborator.copy() for _ in range(2)]
        trending_collaborators[0]['username'] = '热门合作者1'
        trending_collaborators[1]['username'] = '热门合作者2'
        new_collaborators = [mock_collaborator.copy() for _ in range(2)]
        new_collaborators[0]['username'] = '新晋合作者1'
        new_collaborators[1]['username'] = '新晋合作者2'
    
    return render_template(
        'advertiser/home/recommended.html', 
        active_tab='recommended',
        trending_collaborators=trending_collaborators,
        new_collaborators=new_collaborators,
        recommended_collaborators=recommended_collaborators
    ) 