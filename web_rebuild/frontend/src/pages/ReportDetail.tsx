import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Steps, Tabs, Table, Button, message, Spin, Typography, Tag, Space } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { ReportSummary, PipelineNodes, RawArticle, HotTopic, StockPool1, StockPool2 } from '@/types';
import { reportsApi, pipelineApi } from '@/services/api';

const { Title, Text } = Typography;
const { Step } = Steps;

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [pipelineData, setPipelineData] = useState<PipelineNodes | null>(null);
  const [activeNode, setActiveNode] = useState('step1');

  useEffect(() => {
    if (id) {
      loadReportData(parseInt(id));
    }
  }, [id]);

  const loadReportData = async (reportId: number) => {
    try {
      setLoading(true);
      const [summaryRes, nodesRes] = await Promise.all([
        reportsApi.summary(reportId),
        pipelineApi.getNodes(reportId),
      ]);
      if (summaryRes.data.code === 0) {
        setSummary(summaryRes.data.data || null);
      }
      if (nodesRes.data.code === 0) {
        setPipelineData(nodesRes.data.data || null);
      }
    } catch (error) {
      message.error('加载报告数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await reportsApi.generate(parseInt(id));
      if (res.data.code === 0) {
        message.success('开始生成报告...');
        setTimeout(() => loadReportData(parseInt(id)), 2000);
      }
    } catch (error) {
      message.error('生成报告失败');
    } finally {
      setLoading(false);
    }
  };

  const getCurrentStep = () => {
    if (!summary) return 0;
    if (summary.pool2_count > 0) return 4;
    if (summary.pool1_count > 0) return 3;
    if (summary.topic_count > 0) return 2;
    if (summary.article_count > 0) return 1;
    return 0;
  };

  const renderStep1Content = () => {
    const data = pipelineData?.step1.data || [];
    const columns = [
      { title: '标题', dataIndex: 'title', key: 'title' },
      { title: '来源', dataIndex: 'source_account', key: 'source_account' },
      { title: '链接', dataIndex: 'url', key: 'url', ellipsis: true },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    );
  };

  const renderStep2Content = () => {
    const data = pipelineData?.step2.data || [];
    const columns = [
      { title: '热点名称', dataIndex: 'topic_name', key: 'topic_name' },
      { title: '关联板块', dataIndex: 'related_boards', key: 'related_boards',
        render: (boards: string[]) => (
          <Space size={[4, 4]} wrap>
            {boards?.map((b, i) => <Tag key={i}>{b}</Tag>)}
          </Space>
        ),
      },
      { title: '逻辑摘要', dataIndex: 'logic_summary', key: 'logic_summary' },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    );
  };

  const renderStep3Content = () => {
    const data = pipelineData?.step3.data || [];
    const columns = [
      { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
      { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name' },
      { title: '入选理由', dataIndex: 'match_reason', key: 'match_reason' },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    );
  };

  const renderStep4Content = () => {
    const data = (pipelineData?.step4.data || []).filter((s: StockPool2) => s.is_selected);
    const columns = [
      { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
      { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name' },
      { title: '技术面评分', dataIndex: 'tech_score', key: 'tech_score',
        render: (score: number) => score?.toFixed(2),
      },
      { title: '基本面评分', dataIndex: 'fund_score', key: 'fund_score',
        render: (score: number) => score?.toFixed(2),
      },
      { title: '总分', dataIndex: 'total_score', key: 'total_score',
        render: (score: number) => score?.toFixed(2),
      },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
    );
  };

  const stepItems = [
    { title: '情报源', key: 'step1' },
    { title: '热点风口', key: 'step2' },
    { title: '异动初筛', key: 'step3' },
    { title: '深度精选', key: 'step4' },
  ];

  return (
    <Spin spinning={loading}>
      <div>
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card
              title={summary?.report_date || '报告详情'}
              extra={
                <Space>
                  <Tag color={summary?.status === 'completed' ? 'success' : 'processing'}>
                    {summary?.status === 'completed' ? '已完成' :
                     summary?.status === 'processing' ? '处理中' :
                     summary?.status === 'error' ? '错误' : '待处理'}
                  </Tag>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleGenerate}
                  >
                    生成报告
                  </Button>
                </Space>
              }
            >
              <Row gutter={16}>
                <Col span={6}>
                  <Card size="small" type="inner" title="文章数">
                    <Title level={3}>{summary?.article_count || 0}</Title>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" type="inner" title="热点数">
                    <Title level={3}>{summary?.topic_count || 0}</Title>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" type="inner" title="初筛股票">
                    <Title level={3}>{summary?.pool1_count || 0}</Title>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card size="small" type="inner" title="精选股票">
                    <Title level={3}>{summary?.pool2_count || 0}</Title>
                  </Card>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col span={24}>
            <Card title="选股流程">
              <Steps
                current={getCurrentStep()}
                items={stepItems}
                onChange={(index) => setActiveNode(stepItems[index].key)}
              />
            </Card>
          </Col>

          <Col span={24}>
            <Card title="过程数据">
              <Tabs
                activeKey={activeNode}
                onChange={setActiveNode}
                items={[
                  { key: 'step1', label: '情报源', children: renderStep1Content() },
                  { key: 'step2', label: '热点风口', children: renderStep2Content() },
                  { key: 'step3', label: '异动初筛', children: renderStep3Content() },
                  { key: 'step4', label: '深度精选', children: renderStep4Content() },
                ]}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
}
