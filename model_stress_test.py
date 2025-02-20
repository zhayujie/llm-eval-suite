import time
import requests
import concurrent.futures


########################
# 配置参数
########################
URL = "http://127.0.0.1:11434/v1/chat/completions"   # 模型接口地址
MODEL = "deepseek-r1:671b"                           # 模型名称
QUERY = "你是什么模型"                                 # 用户输入问题 (user prompt)
MAX_CONCURRENT = 256                                 # 需要测试的最大并发数
TIMEOUT_THRESHOLD = 180.0                            # 允许的最大响应时间(秒)，平均响应时间超过该值后测试结束
ERROR_THRESHOLD = 0.9                                # 允许的最大错误率，超过该错误率后测试结束


########################
#  运行方式
########################
# python3 stress_test.py


def send_request():
    try:
        start_time = time.time()
        data = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": QUERY}
            ],
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(URL, json=data, headers=headers, timeout=300)
        latency = time.time() - start_time
        if response.status_code == 200:
            res = response.json()
            tokens = res.get("usage").get("completion_tokens")
            # 返回结构: (请求耗时, 是否请求成功, 异常信息, 生成的token数量)
            return latency, True, None, tokens
        else:
            return latency, False, response.text, None
    except Exception as e:
        return None, False, str(e), 0


def stress_test():
    concurrency = 1
    print(f"{MODEL} 压力测试开始...")
    while concurrency <= MAX_CONCURRENT:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(send_request) for _ in range(concurrency)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        latencies = [res[0] for res in results if res[0] is not None]
        tokens = [res[3] for res in results if res[3] is not None]
        success_count = sum(1 for res in results if res[1])
        error_messages = [res[2] for res in results if res[2] is not None]
        error_rate = 1 - (success_count / concurrency)
        if latencies and tokens:
            avg_latency = sum(latencies) / len(latencies)
            avg_tokens = sum(tokens) / len(tokens)
            avg_speed = sum(tokens) / sum(latencies)
        else:
            avg_latency = 0
            avg_tokens = 0
            avg_speed = 0

        print(f"并发请求数: {concurrency}, 平均tokens: {avg_tokens:.2f}, 平均耗时: {avg_latency:.2f}s, 平均速率: {round(avg_speed, 2)} tokens/s")
        if error_messages:
            for error in error_messages:
                print(f"接口调用异常: error={error}")

        if avg_latency > TIMEOUT_THRESHOLD or error_rate > ERROR_THRESHOLD:
            print(f"达到性能瓶颈，测试结束, 平均耗时={avg_latency}, 错误率={error_rate}")
            break

        concurrency *= 2


if __name__ == "__main__":
    stress_test()
