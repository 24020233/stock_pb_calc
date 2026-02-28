import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Steps, Tabs, Table, Button, message, Spin, Typography, Tag, Space, Progress } from 'antd';
import { PlayCircleOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { ReportSummary, PipelineNodes, StockPool2 } from '@/types';
import { reportsApi, pipelineApi } from '@/services/api';

const { Title, Text } = Typography;

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [pipelineData, setPipelineData] = useState<PipelineNodes | null>(null);
  const [activeNode, setActiveNode] = useState('step1');
  const [isPolling, setIsPolling] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Load report data
  const loadReportData = useCallback(async (reportId: number) => {
    try {
      const [summaryRes, nodesRes] = await Promise.all([
        reportsApi.summary(reportId),
        pipelineApi.getNodes(reportId),
      ]);
      if (summaryRes.data.code === 0) {
        setSummary(summaryRes.data.data || null);
        // If processing, start polling
        if (summaryRes.data.data?.status === 'processing') {
          setIsPolling(true);
        } else {
          setIsPolling(false);
        }
      }
      if (nodesRes.data.code === 0) {
        setPipelineData(nodesRes.data.data || null);
      }
    } catch (error) {
      message.error('加载报告数据失败');
      setIsPolling(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (id) {
      loadReportData(parseInt(id));
    }
  }, [id, loadReportData]);

  // Polling effect
  useEffect(() => {
    if (isPolling && id) {
      pollingRef.current = setInterval(() => {
        loadReportData(parseInt(id));
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isPolling, id, loadReportData]);

  const handleGenerate = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await reportsApi.generate(parseInt(id));
      if (res.data.code === 0) {
        message.success('已开始生成报告，请稍候...');
        // Start polling for status updates
        setIsPolling(true);
        // Immediate refresh
        loadReportData(parseInt(id));
      } else {
        message.error(res.data.msg || '生成报告失败');
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || '生成报告失败';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = () => {
    if (!summary) return null;
    switch (summary.status) {
      case 'processing':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  const getStatusTag = () => {
    if (!summary) return null;
    const statusConfig: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      error: { color: 'error', text: '错误' },
    };
    const config = statusConfig[summary.status] || statusConfig.pending;
    return <Tag color={config.color} icon={getStatusIcon()}>{config.text}</Tag>;
  };

  const getCurrentStep = () => {
    if (!summary) return 0;
    if (summary.status === 'error') return 0;
    if (summary.pool2_count > 0) return 4;
    if (summary.pool1_count > 0) return 3;
    if (summary.topic_count > 0) return 2;
    if (summary.article_count > 0) return 1;
    return 0;
  };

  const getStepProgress = () => {
    if (!summary) return 0;
    if (summary.status === 'completed') return 100;
    if (summary.status === 'error') return 0;
    // Calculate progress based on completed steps
    let progress = 0;
    if (summary.article_count > 0) progress += 25;
    if (summary.topic_count > 0) progress += 25;
    if (summary.pool1_count > 0) progress += 25;
    if (summary.pool2_count > 0) progress += 25;
    return progress;
  };

  const renderStep1Content = () => {
    const data = pipelineData?.step1.data || [];
    const columns = [
      { title: '标题', dataIndex: 'title', key: 'title' },
      { title: '来源', dataIndex: 'source_account', key: 'source_account', width: 120 },
      {
        title: '链接',
        dataIndex: 'url',
        key: 'url',
        ellipsis: true,
        render: (url: string) => url ? (
          <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#1890ff' }}>
            {url.substring(0, 50)}...
          </a>
        ) : '-'
      },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无数据' }}
      />
    );
  };

  const renderStep2Content = () => {
    const data = pipelineData?.step2.data || [];
    const columns = [
      { title: '热点名称', dataIndex: 'topic_name', key: 'topic_name', width: 200 },
      {
        title: '关联板块',
        dataIndex: 'related_boards',
        key: 'related_boards',
        render: (boards: string[]) => (
          <Space size={[4, 4]} wrap>
            {(boards || []).map((b, i) => <Tag key={i} color="blue">{b}</Tag>)}
          </Space>
        ),
      },
      { title: '逻辑摘要', dataIndex: 'logic_summary', key: 'logic_summary', ellipsis: true },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无数据' }}
      />
    );
  };

  const renderStep3Content = () => {
    const data = pipelineData?.step3.data || [];
    const columns = [
      { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code', width: 100 },
      { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name', width: 100 },
      { title: '入选理由', dataIndex: 'match_reason', key: 'match_reason' },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无数据' }}
      />
    );
  };

  const renderStep4Content = () => {
    const data = (pipelineData?.step4.data || []).filter((s: StockPool2) => s.is_selected);
    const columns = [
      { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code', width: 100 },
      { title: '股票名称', dataIndex: 'stock_name', key: 'stock_name', width: 100 },
      {
        title: '技术面评分',
        dataIndex: 'tech_score',
        key: 'tech_score',
        width: 100,
        render: (score: number) => score?.toFixed(2) || '-',
      },
      {
        title: '基本面评分',
        dataIndex: 'fund_score',
        key: 'fund_score',
        width: 100,
        render: (score: number) => score?.toFixed(2) || '-',
      },
      {
        title: '总分',
        dataIndex: 'total_score',
        key: 'total_score',
        width: 80,
        render: (score: number) => <Text strong>{score?.toFixed(2) || '-'}</Text>,
      },
    ];
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无数据' }}
      />
    );
  };

  const stepItems = [
    {
      title: '情报源',
      key: 'step1',
      status: summary?.article_count ? 'finish' : 'wait'
    },
    {
      title: '热点风口',
      key: 'step2',
      status: summary?.topic_count ? 'finish' : 'wait'
    },
    {
      title: '异动初筛',
      key: 'step3',
      status: summary?.pool1_count ? 'finish' : 'wait'
    },
    {
      title: '深度精选',
      key: 'step4',
      status: summary?.pool2_count ? 'finish' : 'wait'
    },
  ];

  return (
    <Spin spinning={loading}>
      <div>
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card
              title={
                <Space>
                  <span>{summary?.report_date || '报告详情'}</span>
                  {isPolling && <SyncOutlined spin style={{ color: '#1890ff' }} />}
                </Space>
              }
              extra={
                <Space>
                  {getStatusTag()}
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleGenerate}
                    disabled={summary?.status === 'processing'}
                    loading={summary?.status === 'processing'}
                  >
                    {summary?.status === 'processing' ? '生成中...' : '生成报告'}
                  </Button>
                </Space>
              }
            >
              {summary?.status === 'processing' && (
                <div style={{ marginBottom: 16 }}>
                  <Progress
                    percent={getStepProgress()}
                    status="active"
                    format={() => '正在处理...'}
                  />
                </div>
              )}
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
                  { key: 'step1', label: `情报源 (${summary?.article_count || 0})`, children: renderStep1Content() },
                  { key: 'step2', label: `热点风口 (${summary?.topic_count || 0})`, children: renderStep2Content() },
                  { key: 'step3', label: `异动初筛 (${summary?.pool1_count || 0})`, children: renderStep3Content() },
                  { key: 'step4', label: `深度精选 (${summary?.pool2_count || 0})`, children: renderStep4Content() },
                ]}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
}