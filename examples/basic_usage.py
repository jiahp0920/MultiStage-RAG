import asyncio
import yaml
from src.multistage_rag.core.retriever import MultiStageRetriever
from src.multistage_rag.core.models import Document


async def main():
    # 加载配置
    with open("configs/default_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # 创建检索器
    retriever = MultiStageRetriever(config)

    # 添加示例文档
    docs = [
        Document(
            id="doc1",
            content="人工智能是计算机科学的一个分支。",
            metadata={"source": "wikipedia"}
        ),
        Document(
            id="doc2",
            content="机器学习通过数据训练模型。",
            metadata={"source": "textbook"}
        ),
    ]

    await retriever.add_documents(docs)

    # 执行检索
    result = await retriever.retrieve(
        query="什么是人工智能？",
        top_k=3,
        use_cache=True
    )

    # 输出结果
    print(f"查询: {result.query}")
    print(f"阶段: {result.stage.value}")
    print(f"耗时: {result.latency_ms:.2f}ms")
    print(f"文档数: {len(result.documents)}")

    for i, doc in enumerate(result.documents):
        print(f"\n{i + 1}. {doc.content[:50]}...")
        print(f"   分数: {doc.final_score:.4f}")

    # 清理
    await retriever.close()


if __name__ == "__main__":
    asyncio.run(main())