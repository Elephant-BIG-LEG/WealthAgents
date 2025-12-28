from flask import Blueprint, request, jsonify
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback
import json

# 创建API蓝图
financial_api_bp = Blueprint('financial_api', __name__)
logger = logging.getLogger(__name__)

# 添加工具函数，确保JSON序列化支持
class DateTimeEncoder(json.JSONEncoder):
    """处理JSON序列化中的datetime对象"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# 替换jsonify，支持自定义编码器
def custom_jsonify(obj):
    """自定义JSON响应函数，支持更多类型"""
    response = jsonify(obj)
    response.data = json.dumps(obj, cls=DateTimeEncoder, ensure_ascii=False).encode('utf-8')
    response.mimetype = 'application/json'
    return response

# 简单的响应工具函数
def success_response(message="操作成功", data=None, status_code=200):
    """成功响应格式化"""
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    return jsonify(response), status_code

def error_response(message="操作失败", status_code=400):
    """错误响应格式化"""
    response = {
        "success": False,
        "message": message,
        "data": None
    }
    return jsonify(response), status_code

# 导入财务文档处理服务
try:
    # 尝试导入FinancialDocumentProcessor
    from app.services.financial_document_processor import FinancialDocumentProcessor
    financial_processor = FinancialDocumentProcessor()
    
    # 尝试导入其他相关服务
    from app.services.financial_document_utils import EnhancedFinancialTextSplitter, FinancialTagGenerator
    from app.services.financial_vector_store import FinancialVectorStore, create_financial_vector_store, vectorize_financial_documents
    HAS_FINANCIAL_SERVICES = True
except ImportError as e:
    logger.warning(f"无法导入财务服务模块: {str(e)}")
    HAS_FINANCIAL_SERVICES = False


@financial_api_bp.route('/document/upload', methods=['POST'])
def upload_financial_documents():
    """
    上传财务分析文档并构建财务知识库
    """
    try:
        # 检查是否有财务服务可用
        if not HAS_FINANCIAL_SERVICES:
            return error_response("财务分析服务未初始化，请检查相关模块")
        
        # 获取公司名称
        company_name = request.form.get('company_name')
        if not company_name or company_name.strip() == '':
            return error_response("公司名称不能为空")
        
        # 获取上传的文件
        files = request.files.getlist('financial_documents')
        if not files or len(files) == 0:
            return error_response("请至少上传一个财务文档文件")
        
        # 获取文档元数据信息
        document_types = request.form.get('document_types', '')
        document_types = [t.strip() for t in document_types.split(',')] if document_types else []
        
        years = request.form.get('years', '')
        years = [int(y.strip()) if y.strip().isdigit() else None for y in years.split(',')] if years else []
        
        quarters = request.form.get('quarters', '')
        quarters = [q.strip() for q in quarters.split(',')] if quarters else []
        
        # 处理上传的文件
        financial_documents = []
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            try:
                # 保存临时文件
                temp_dir = os.path.join(os.getcwd(), 'temp_uploads')
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, file.filename)
                
                file.save(temp_path)
                logger.info(f"已保存临时文件: {temp_path}")
                
                # 处理文件并提取财务内容
                file_result = financial_processor.process_financial_file(temp_path)
                
                # 构建文档对象
                document = {
                    'file_name': file.filename,
                    'content': file_result['content'],
                    'document_type': document_types[i] if i < len(document_types) else 'financial_report',
                    'upload_time': datetime.now().isoformat(),
                    'source': 'upload'
                }
                
                # 添加年份和季度信息（如果有）
                if i < len(years) and years[i] is not None:
                    document['year'] = years[i]
                
                if i < len(quarters):
                    document['quarter'] = quarters[i]
                
                financial_documents.append(document)
                
            except Exception as e:
                logger.error(f"处理文件 {file.filename} 时出错: {str(e)}")
                logger.debug(traceback.format_exc())
                continue
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
        
        if not financial_documents:
            return error_response("无法处理上传的文件，请检查文件格式是否支持")
        
        # 构建财务知识库
        result = build_financial_knowledge_base(company_name, financial_documents)
        
        if result.get('status') == 'success':
            return success_response(
                message=f"公司 {company_name} 财务知识库构建成功",
                data=result.get('statistics', {})
            )
        else:
            return error_response(result.get('message', '财务知识库构建失败'))
            
    except Exception as e:
        logger.error(f"上传财务文档时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return error_response(f"处理请求时发生错误: {str(e)}")


def build_financial_knowledge_base(company_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建财务知识库的核心函数
    """
    try:
        # 创建财务向量存储
        vector_store = create_financial_vector_store(company_name)
        logger.info(f"为公司 {company_name} 创建了财务向量存储")
        
        # 创建统计数据对象
        statistics = {
            'total_documents': len(documents),
            'processed_documents': 0,
            'total_chunks': 0,
            'total_tags': 0,
            'stored_vectors': 0,
            'errors': []
        }
        
        # 处理每个文档
        for doc_idx, document in enumerate(documents):
            try:
                # 1. 文档分块
                logger.info(f"开始处理文档 {doc_idx + 1}/{len(documents)}: {document['file_name']}")
                
                # 创建增强的财务文本分割器
                splitter = EnhancedFinancialTextSplitter(
                    chunk_size=800, 
                    chunk_overlap=150
                )
                
                # 分割文档内容
                chunks = splitter.split_text(document['content'])
                statistics['total_chunks'] += len(chunks)
                logger.info(f"文档分割完成，共生成 {len(chunks)} 个文本块")
                
                # 2. 为每个文本块添加财务标签
                tag_generator = FinancialTagGenerator()
                documents_with_metadata = []
                
                for chunk_idx, chunk in enumerate(chunks):
                    # 生成财务标签
                    tags = tag_generator.generate_content_tags(chunk)
                    statistics['total_tags'] += len(tags)
                    
                    # 生成元数据
                    metadata = {
                        'document_index': doc_idx,
                        'chunk_index': chunk_idx,
                        'file_name': document['file_name'],
                        'document_type': document.get('document_type', 'financial_report'),
                        'financial_tags': tags,
                        'upload_time': document.get('upload_time', datetime.now().isoformat())
                    }
                    
                    # 添加年份和季度信息（如果有）
                    if 'year' in document:
                        metadata['year'] = document['year']
                    
                    if 'quarter' in document:
                        metadata['quarter'] = document['quarter']
                    
                    # 增强元数据生成
                    enhanced_metadata = tag_generator.generate_enhanced_metadata(document['file_name'], chunk, metadata)
                    
                    # 添加到文档列表
                    documents_with_metadata.append({
                        'text': chunk,
                        'metadata': enhanced_metadata
                    })
                
                # 3. 向量化文档
                vectorization_result = vectorize_financial_documents(documents_with_metadata)
                
                if vectorization_result['statistics']['error_count'] > 0:
                    logger.warning(f"向量化过程中有错误: {vectorization_result['statistics']['errors']}")
                    statistics['errors'].extend(vectorization_result['statistics']['errors'])
                
                # 4. 存储向量到数据库
                if vectorization_result['vectors'].size > 0:
                    # 从向量化结果中提取文本和元数据
                    texts = vectorization_result['texts']
                    vectors = vectorization_result['vectors']
                    metadata = vectorization_result['metadata']
                    
                    # 添加到向量存储
                    store_result = vector_store.add_vectors(texts, vectors, metadata=metadata)
                    
                    if store_result:
                        statistics['stored_vectors'] += len(texts)
                        logger.info(f"成功存储 {len(texts)} 个向量到数据库")
                    else:
                        logger.error(f"向量存储失败")
                        statistics['errors'].append("向量存储失败")
                
                statistics['processed_documents'] += 1
                
            except Exception as e:
                error_msg = f"处理文档 {document.get('file_name', 'unknown')} 时出错: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                statistics['errors'].append(error_msg)
        
        # 保存统计信息
        statistics_path = os.path.join(
            vector_store.storage_path,
            "financial_knowledge_statistics.json"
        )
        
        with open(statistics_path, 'w', encoding='utf-8') as f:
            json.dump({
                'company_name': company_name,
                'build_time': datetime.now().isoformat(),
                'statistics': statistics
            }, f, ensure_ascii=False, indent=2)
        
        # 返回成功结果
        return {
            'status': 'success',
            'message': f"财务知识库构建完成",
            'statistics': statistics,
            'knowledge_base_path': vector_store.storage_path
        }
        
    except Exception as e:
        logger.error(f"构建财务知识库时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            'status': 'error',
            'message': str(e)
        }


@financial_api_bp.route('/knowledge/query', methods=['POST'])
def query_financial_knowledge():
    """
    查询财务知识库
    """
    try:
        # 检查是否有财务服务可用
        if not HAS_FINANCIAL_SERVICES:
            return error_response("财务分析服务未初始化，请检查相关模块")
        
        # 获取请求参数
        company_name = request.form.get('company_name')
        query_text = request.form.get('query_text')
        top_k = request.form.get('top_k', 5, type=int)
        year_filter = request.form.get('year_filter', type=int)
        quarter_filter = request.form.get('quarter_filter')
        tags_filter = request.form.get('tags_filter')
        
        # 处理标签过滤
        tags_filter = [t.strip() for t in tags_filter.split(',')] if tags_filter else None
        
        if not company_name or not query_text:
            return error_response("公司名称和查询文本不能为空")
        
        # 创建向量存储实例
        try:
            vector_store = create_financial_vector_store(company_name)
        except Exception as e:
            logger.error(f"创建向量存储失败: {str(e)}")
            return error_response(f"公司 {company_name} 的财务知识库不存在", status_code=404)
        
        # 检查向量存储是否存在
        if vector_store.get_vector_count() == 0:
            return error_response(f"公司 {company_name} 的财务知识库为空或不存在", status_code=404)
        
        # 向量化查询文本
        try:
            from app.Embedding.Vectorization import TextVectorizer
            vectorizer = TextVectorizer()
            query_vector = vectorizer.vectorize_text(query_text)
        except ImportError:
            logger.error("无法导入TextVectorizer")
            return error_response("文本向量化模块不可用")
        
        # 执行带过滤条件的搜索
        results = vector_store.search_similar_with_filter(
            query_vector=query_vector,
            top_k=top_k,
            year_filter=year_filter,
            quarter_filter=quarter_filter,
            tags_filter=tags_filter
        )
        
        # 格式化结果
        formatted_results = []
        for text, similarity, metadata in results:
            formatted_results.append({
                'text': text,
                'similarity': float(similarity),
                'metadata': metadata
            })
        
        return success_response(
            message="财务知识查询成功",
            data={
                'company_name': company_name,
                'query_text': query_text,
                'results_count': len(formatted_results),
                'results': formatted_results
            }
        )
        
    except Exception as e:
        logger.error(f"查询财务知识库时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return error_response(f"查询失败: {str(e)}")


@financial_api_bp.route('/companies/list', methods=['GET'])
def list_financial_companies():
    """
    列出所有已构建财务知识库的公司
    """
    try:
        # 获取知识库根目录
        kb_root_path = os.path.join(os.getcwd(), "financial_analysis_knowledge_base")
        
        # 检查目录是否存在
        if not os.path.exists(kb_root_path):
            return success_response(
                message="没有找到财务知识库",
                data=[]
            )
        
        # 列出所有公司目录
        companies = []
        for company_dir in os.listdir(kb_root_path):
            company_path = os.path.join(kb_root_path, company_dir)
            
            # 检查是否为目录且包含向量存储
            if os.path.isdir(company_path):
                vector_store_path = os.path.join(company_path, "financial_vector_store")
                if os.path.exists(vector_store_path):
                    # 读取统计信息
                    stats_path = os.path.join(vector_store_path, "financial_knowledge_statistics.json")
                    company_info = {
                        'name': company_dir.replace('_', ' '),  # 将下划线替换回空格
                        'vector_store_path': vector_store_path
                    }
                    
                    # 如果存在统计信息，读取它
                    if os.path.exists(stats_path):
                        try:
                            with open(stats_path, 'r', encoding='utf-8') as f:
                                stats_data = json.load(f)
                                company_info['build_time'] = stats_data.get('build_time', '')
                                company_info['statistics'] = stats_data.get('statistics', {})
                        except:
                            pass
                    
                    companies.append(company_info)
        
        return success_response(
            message="获取财务知识库公司列表成功",
            data=companies
        )
        
    except Exception as e:
        logger.error(f"获取财务知识库公司列表时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return error_response(f"获取失败: {str(e)}")


@financial_api_bp.route('/knowledge/delete', methods=['DELETE'])
def delete_financial_knowledge():
    """
    删除公司财务知识库
    """
    try:
        # 获取公司名称
        company_name = request.form.get('company_name')
        if not company_name or company_name.strip() == '':
            return error_response("公司名称不能为空")
        
        # 构建知识库路径
        kb_root_path = os.path.join(os.getcwd(), "financial_analysis_knowledge_base")
        company_dir = company_name.replace(' ', '_')  # 将空格替换为下划线
        company_path = os.path.join(kb_root_path, company_dir)
        
        # 检查知识库是否存在
        if not os.path.exists(company_path):
            return error_response(f"公司 {company_name} 的财务知识库不存在", status_code=404)
        
        # 删除整个公司目录
        import shutil
        shutil.rmtree(company_path)
        
        return success_response(
            message=f"公司 {company_name} 的财务知识库删除成功",
            data={'company_name': company_name}
        )
        
    except Exception as e:
        logger.error(f"删除财务知识库时出错: {str(e)}")
        logger.debug(traceback.format_exc())
        return error_response(f"删除失败: {str(e)}")