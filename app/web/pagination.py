from flask_paginate import Pagination, get_page_parameter
from flask import request, url_for

def create_pagination(total_items, page_param=None, per_page=10, css_framework='bootstrap5', record_name='记录'):
    """创建通用分页对象，可在全站复用#生成标准化分页控件"""
    page = request.args.get(page_param or get_page_parameter(), 1, type=int)
    
    # 创建分页对象
    pagination = Pagination(
        page=page,
        per_page=per_page,
        total=total_items,
        css_framework=css_framework,
        prev_label='<i class="bi bi-chevron-left"></i>',
        next_label='<i class="bi bi-chevron-right"></i>',
        alignment='center',
        link_size='sm',
        show_single_page=False,
        record_name=record_name
    )
    
    # 计算当前页的数据范围
    offset = (page - 1) * per_page
    limit = per_page
    
    return {
        'pagination': pagination,
        'page': page,
        'per_page': per_page,
        'offset': offset,
        'limit': limit
    } 