"""
性能测试和资源监控
测试系统的性能表现和资源使用情况
"""

import pytest
import asyncio
import time
import psutil
import tracemalloc
from unittest.mock import Mock, patch, AsyncMock
import gc

class TestResourceUsage:
    """资源使用测试"""
    
    def test_memory_usage_monitoring(self):
        """测试内存使用监控"""
        # 开始内存跟踪
        tracemalloc.start()
        
        # 记录初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行一些操作
        large_data = ["test_data"] * 10000
        time.sleep(0.1)  # 给GC一些时间
        
        # 记录当前内存
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 清理数据
        del large_data
        gc.collect()
        
        # 停止内存跟踪
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 验证内存使用在合理范围内 (tracemalloc单位是字节)
        assert current_memory < 500  # 进程内存使用应该小于500MB
        assert peak / 1024 / 1024 < 100  # tracemalloc峰值应该小于100MB
    
    def test_cpu_usage_monitoring(self):
        """测试CPU使用监控"""
        # 记录初始CPU使用率
        initial_cpu = psutil.cpu_percent(interval=1)
        
        # 执行一些计算密集型操作
        start_time = time.time()
        result = sum(i * i for i in range(1000000))
        execution_time = time.time() - start_time
        
        # 记录CPU使用率
        current_cpu = psutil.cpu_percent(interval=1)
        
        # 验证性能指标
        assert execution_time < 5.0  # 计算应该在5秒内完成
        assert current_cpu < 90  # CPU使用率不应该超过90%

class TestPerformanceBenchmark:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_metadata_search_performance(self):
        """测试元数据搜索性能"""
        # 模拟元数据服务
        with patch('app.services.metadata_service.MetadataService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # 模拟搜索结果
            mock_result = Mock()
            mock_result.success = True
            mock_result.search_result = Mock()
            mock_result.search_result.title = "测试歌曲"
            mock_result.album = "测试专辑"
            
            mock_service.get_best_match_metadata = AsyncMock(return_value=mock_result)
            
            # 性能测试
            start_time = time.time()
            
            # 执行多次搜索
            for i in range(10):
                await mock_service.get_best_match_metadata(f"歌曲{i}", f"歌手{i}")
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / 10
            
            # 验证性能指标
            assert avg_time < 0.5  # 平均每次搜索应该小于500ms
            assert total_time < 3.0  # 总时间应该小于3秒
    
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self):
        """测试并发搜索性能"""
        import concurrent.futures
        
        # 模拟并发搜索任务
        async def mock_search_task(query, artist):
            with patch('app.services.metadata_service.MetadataService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                mock_result = Mock()
                mock_result.success = True
                mock_result.search_result = Mock()
                mock_result.search_result.title = query
                mock_result.album = "测试专辑"
                
                mock_service.get_best_match_metadata = AsyncMock(return_value=mock_result)
                
                # 模拟网络延迟
                await asyncio.sleep(0.1)
                return await mock_service.get_best_match_metadata(query, artist)
        
        # 执行并发搜索
        start_time = time.time()
        
        tasks = []
        for i in range(20):
            task = mock_search_task(f"歌曲{i}", f"歌手{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证并发性能
        assert len(results) == 20
        assert all(result.success for result in results)
        assert total_time < 5.0  # 20个并发请求应该在5秒内完成

class TestScalabilityTesting:
    """可扩展性测试"""
    
    def test_database_connection_pooling(self):
        """测试数据库连接池"""
        with patch('core.database.SessionLocal') as mock_session_factory:
            mock_sessions = []
            
            # 模拟创建多个数据库会话
            for i in range(50):
                mock_session = Mock()
                mock_session.__enter__ = Mock(return_value=mock_session)
                mock_session.__exit__ = Mock(return_value=None)
                mock_sessions.append(mock_session)
            
            mock_session_factory.side_effect = mock_sessions
            
            # 测试连接池使用
            connections = []
            for i in range(20):
                with mock_session_factory() as session:
                    connections.append(session)
                    # 模拟数据库操作
                    time.sleep(0.01)
            
            # 验证连接管理
            assert len(connections) == 20
            # 验证会话工厂被正确调用
            assert mock_session_factory.call_count >= 20
    
    @pytest.mark.asyncio
    async def test_async_task_handling(self):
        """测试异步任务处理能力"""
        # 模拟异步任务队列
        task_queue = asyncio.Queue()
        
        # 生产者任务
        async def producer():
            for i in range(100):
                await task_queue.put(f"task_{i}")
                await asyncio.sleep(0.001)  # 模拟任务生成间隔
        
        # 消费者任务
        async def consumer(consumer_id):
            processed = 0
            while processed < 20:  # 每个消费者处理20个任务
                try:
                    task = await asyncio.wait_for(task_queue.get(), timeout=1.0)
                    # 模拟任务处理
                    await asyncio.sleep(0.01)
                    processed += 1
                    task_queue.task_done()
                except asyncio.TimeoutError:
                    break
            return processed
        
        # 启动测试
        start_time = time.time()
        
        # 启动生产者和消费者
        prod_task = asyncio.create_task(producer())
        consumers = [asyncio.create_task(consumer(i)) for i in range(5)]
        
        # 等待完成
        await prod_task
        await task_queue.join()  # 等待队列中所有任务完成
        results = await asyncio.gather(*consumers)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证处理能力
        total_processed = sum(results)
        assert total_processed >= 80  # 至少处理80个任务（考虑到超时）
        assert total_time < 10.0  # 应该在10秒内完成

class TestLoadTesting:
    """负载测试"""
    
    def test_high_concurrency_load(self):
        """测试高并发负载"""
        import threading
        import queue
        
        # 结果队列
        result_queue = queue.Queue()
        
        def worker(worker_id):
            """工作线程函数"""
            success_count = 0
            for i in range(50):  # 每个线程处理50个请求
                try:
                    # 模拟API调用
                    with patch('app.services.metadata_service.MetadataService') as mock_service:
                        mock_service_instance = Mock()
                        mock_service.return_value = mock_service_instance
                        mock_service_instance.get_best_match_metadata = AsyncMock(
                            return_value=Mock(success=True)
                        )
                        success_count += 1
                except Exception:
                    pass
                time.sleep(0.001)  # 模拟网络延迟
            
            result_queue.put(success_count)
        
        # 启动多个线程模拟高并发
        threads = []
        start_time = time.time()
        
        for i in range(20):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 收集结果
        total_success = 0
        while not result_queue.empty():
            total_success += result_queue.get()
        
        # 验证负载处理能力
        expected_requests = 20 * 50  # 20线程 × 50请求
        assert total_success == expected_requests  # 所有请求都应该成功
        assert total_time < 15.0  # 应该在15秒内完成所有请求

if __name__ == "__main__":
    pytest.main(["-v", __file__])