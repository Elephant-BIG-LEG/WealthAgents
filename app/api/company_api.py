from flask import Blueprint, request, jsonify
import os
import logging
from datetime import datetime
from typing import Dict, Any

# 导入我们创建的服务
try:
    from app.services.company_knowledge_manager import knowledge_manager
    from app.services.document_processor import document_processor, file_upload_handler
    from app.services.financial_analyzer import financial_analyzer
    from app.utils.response_utils import success_response, error_response
    from app.utils.auth_utils import require_auth
    has_dependencies = True
except ImportError as e:
    logging.error(f"导入依赖失败: {str(e)}")
    has_dependencies = False

# 创建API蓝图
company_api = Blueprint('company_api', __name__, url_prefix='/api/company')
logger = logging.getLogger(__name__)


@company_api.route('/knowledge/upload', methods=['POST'])
def upload_company_documents():
    """
    上传公司文档并构建知识库
    ---
    tags:
      - Company Knowledge Base
    parameters:
      - in: formData
        name: company_name
        type: string
        required: true
        description: 公司名称
      - in: formData
        name: documents
        type: file
        required: true
        description: 上传的文档文件
      - in: formData
        name: document_types
        type: string
        required: false
        description: 文档类型，以逗号分隔，与上传文件顺序对应
      - in: formData
        name: years
        type: string
        required: false
        description: 年份，以逗号分隔，与上传文件顺序对应
    responses:
      200:
        description: 上传成功并已构建知识库
      400:
        description: 请求参数错误
      500:
        description: 服务器内部错误
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        # 获取公司名称
        company_name = request.form.get('company_name')
        if not company_name or company_name.strip() == '':
            return error_response("公司名称不能为空")
        
        # 获取上传的文件
        files = request.files.getlist('documents')
        if not files or len(files) == 0:
            return error_response("请至少上传一个文档文件")
        
        # 获取文档类型和年份信息
        document_types = request.form.get('document_types', '')
        document_types = [t.strip() for t in document_types.split(',')] if document_types else []
        
        years = request.form.get('years', '')
        years = [int(y.strip()) if y.strip().isdigit() else None for y in years.split(',')] if years else []
        
        # 处理上传的文件
        documents = []
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            try:
                # 保存临时文件
                file_content = file.read()
                temp_path = file_upload_handler.save_uploaded_file(file_content, file.filename)
                
                # 处理文件并提取文本
                file_result = document_processor.process_file(temp_path, file.filename)
                
                # 构建文档对象
                document = {
                    'file_name': file_result['file_name'],
                    'content': file_result['content'],
                    'document_type': document_types[i] if i < len(document_types) else 'general',
                    'upload_time': datetime.now().isoformat()
                }
                
                # 添加年份信息（如果有）
                if i < len(years) and years[i] is not None:
                    document['year'] = years[i]
                
                documents.append(document)
                
            except Exception as e:
                logger.error(f"处理文件 {file.filename} 时出错: {str(e)}")
                continue
        
        if not documents:
            return error_response("无法处理上传的文件，请检查文件格式是否支持")
        
        # 构建公司知识库
        result = knowledge_manager.add_company_knowledge(company_name, documents)
        
        # 清理临时文件
        file_upload_handler.cleanup_uploads()
        
        if result.get('status') == 'success':
            return success_response(
                message=f"公司 {company_name} 知识库构建成功",
                data=result.get('statistics', {})
            )
        else:
            return error_response(result.get('message', '知识库构建失败'))
            
    except Exception as e:
        logger.error(f"上传公司文档时出错: {str(e)}")
        file_upload_handler.cleanup_uploads()  # 确保清理临时文件
        return error_response(f"处理请求时发生错误: {str(e)}")


@company_api.route('/knowledge/query', methods=['GET'])
def query_company_knowledge():
    """
    查询公司知识库
    ---
    tags:
      - Company Knowledge Base
    parameters:
      - in: query
        name: company_name
        type: string
        required: true
        description: 公司名称
      - in: query
        name: query_text
        type: string
        required: true
        description: 查询文本
      - in: query
        name: top_k
        type: integer
        required: false
        description: 返回结果数量，默认5
    responses:
      200:
        description: 查询成功
      400:
        description: 请求参数错误
      404:
        description: 公司知识库不存在
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        # 获取请求参数
        company_name = request.args.get('company_name')
        query_text = request.args.get('query_text')
        top_k = request.args.get('top_k', 5, type=int)
        
        if not company_name or not query_text:
            return error_response("公司名称和查询文本不能为空")
        
        # 验证公司是否存在
        if company_name not in knowledge_manager.list_companies():
            return error_response(f"公司 {company_name} 的知识库不存在", status_code=404)
        
        # 查询知识库
        results = knowledge_manager.query_company_knowledge(company_name, query_text, top_k)
        
        return success_response(
            message="查询成功",
            data={
                'company_name': company_name,
                'query_text': query_text,
                'results': results
            }
        )
        
    except Exception as e:
        logger.error(f"查询公司知识库时出错: {str(e)}")
        return error_response(f"查询失败: {str(e)}")


@company_api.route('/knowledge/list', methods=['GET'])
def list_companies():
    """
    列出所有已构建知识库的公司
    ---
    tags:
      - Company Knowledge Base
    responses:
      200:
        description: 获取成功
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        companies = knowledge_manager.list_companies()
        companies_info = []
        
        for company in companies:
            info = knowledge_manager.get_company_info(company)
            if info:
                companies_info.append({
                    'name': company,
                    'document_count': info.get('document_count', 0),
                    'chunk_count': info.get('chunk_count', 0),
                    'last_updated': info.get('last_updated', '')
                })
        
        return success_response(
            message="获取成功",
            data=companies_info
        )
        
    except Exception as e:
        logger.error(f"获取公司列表时出错: {str(e)}")
        return error_response(f"获取失败: {str(e)}")


@company_api.route('/knowledge/<company_name>', methods=['DELETE'])
def delete_company_knowledge(company_name):
    """
    删除公司知识库
    ---
    tags:
      - Company Knowledge Base
    parameters:
      - in: path
        name: company_name
        type: string
        required: true
        description: 公司名称
    responses:
      200:
        description: 删除成功
      404:
        description: 公司知识库不存在
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        # 验证公司是否存在
        if company_name not in knowledge_manager.list_companies():
            return error_response(f"公司 {company_name} 的知识库不存在", status_code=404)
        
        # 删除知识库
        success = knowledge_manager.delete_company_knowledge(company_name)
        
        if success:
            return success_response(message=f"公司 {company_name} 的知识库已成功删除")
        else:
            return error_response(f"删除公司 {company_name} 的知识库时出错")
            
    except Exception as e:
        logger.error(f"删除公司知识库时出错: {str(e)}")
        return error_response(f"删除失败: {str(e)}")


@company_api.route('/financial/analyze', methods=['POST'])
def analyze_company_financial():
    """
    分析公司财务数据
    ---
    tags:
      - Financial Analysis
    parameters:
      - in: body
        name: request
        schema:
          type: object
          required:
            - company_name
          properties:
            company_name:
              type: string
              description: 公司名称
            financial_data:
              type: object
              description: 财务数据字典
            use_knowledge_base:
              type: boolean
              description: 是否使用知识库中的数据进行分析，默认为false
    responses:
      200:
        description: 分析成功
      400:
        description: 请求参数错误
      404:
        description: 公司或财务数据不存在
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'company_name' not in data:
            return error_response("缺少必要的请求参数")
        
        company_name = data.get('company_name')
        use_knowledge_base = data.get('use_knowledge_base', False)
        financial_data = data.get('financial_data', {})
        
        # 分析逻辑
        if use_knowledge_base:
            # 从知识库中分析财务数据
            if company_name not in knowledge_manager.list_companies():
                return error_response(f"公司 {company_name} 的知识库不存在", status_code=404)
            
            result = financial_analyzer.analyze_company_from_knowledge_base(
                company_name, knowledge_manager
            )
            
            if result.get('status') == 'success':
                return success_response(
                    message=f"从知识库中分析公司 {company_name} 财务状况成功",
                    data=result.get('analysis_results', {})
                )
            else:
                return error_response(
                    result.get('message', '从知识库分析失败'),
                    status_code=404 if result.get('status') == 'insufficient_data' else 500
                )
        else:
            # 使用提供的财务数据进行分析
            if not financial_data:
                return error_response("请提供财务数据或使用知识库选项")
            
            result = financial_analyzer.analyze_financial_data(company_name, financial_data)
            
            if 'error' not in result:
                return success_response(
                    message=f"分析公司 {company_name} 财务数据成功",
                    data=result
                )
            else:
                return error_response(result.get('error', '分析失败'))
                
    except Exception as e:
        logger.error(f"分析公司财务数据时出错: {str(e)}")
        return error_response(f"分析失败: {str(e)}")


@company_api.route('/financial/report', methods=['POST'])
def generate_financial_report():
    """
    生成格式化的财务分析报告
    ---
    tags:
      - Financial Analysis
    parameters:
      - in: body
        name: request
        schema:
          type: object
          required:
            - company_name
            - analysis_results
          properties:
            company_name:
              type: string
              description: 公司名称
            analysis_results:
              type: object
              description: 财务分析结果
    responses:
      200:
        description: 报告生成成功
      400:
        description: 请求参数错误
    """
    try:
        # 检查依赖是否加载成功
        if not has_dependencies:
            return error_response("系统依赖加载失败，请检查服务配置")
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'company_name' not in data or 'analysis_results' not in data:
            return error_response("缺少必要的请求参数")
        
        company_name = data.get('company_name')
        analysis_results = data.get('analysis_results')
        
        # 生成报告
        report = financial_analyzer.generate_financial_report(company_name, analysis_results)
        
        return success_response(
            message="财务分析报告生成成功",
            data={
                'report': report,
                'format': 'markdown'
            }
        )
        
    except Exception as e:
        logger.error(f"生成财务报告时出错: {str(e)}")
        return error_response(f"报告生成失败: {str(e)}")


# 工具函数（如果未导入utils模块，提供默认实现）
def success_response(message: str = "成功", data: Any = None, status_code: int = 200) -> dict:
    """返回成功响应"""
    response = {
        "code": 200,
        "message": message,
        "data": data if data is not None else {}
    }
    return jsonify(response), status_code

def error_response(message: str = "失败", data: Any = None, status_code: int = 400) -> dict:
    """返回错误响应"""
    response = {
        "code": status_code,
        "message": message,
        "data": data if data is not None else {}
    }
    return jsonify(response), status_code

def require_auth(func):
    """认证装饰器（简单实现）"""
    def wrapper(*args, **kwargs):
        # 这里可以实现认证逻辑，目前暂时直接通过
        # 实际项目中应根据需求实现JWT或Session认证
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# 注册API蓝图的函数
def register_company_api(app):
    """
    将公司API蓝图注册到Flask应用
    """
    app.register_blueprint(company_api)
    logger.info("公司API蓝图注册成功")
