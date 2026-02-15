import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, List, Typography, Modal, DatePicker, message, Spin } from 'antd';
import { PlusOutlined, CalendarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Report } from '@/types';
import { reportsApi } from '@/services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  useEffect(() => {
    loadRecentReports();
  }, []);

  const loadRecentReports = async () => {
    try {
      setLoading(true);
      const res = await reportsApi.list({ limit: 5 });
      if (res.data.code === 0) {
        setReports(res.data.data?.reports || []);
      }
    } catch (error) {
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReport = async () => {
    try {
      setLoading(true);
      const res = await reportsApi.create({
        report_date: selectedDate.format('YYYY-MM-DD'),
      });
      if (res.data.code === 0) {
        message.success('创建报告成功');
        setCreateModalVisible(false);
        const reportId = res.data.data?.id;
        if (reportId) {
          navigate(`/reports/${reportId}`);
        } else {
          loadRecentReports();
        }
      }
    } catch (error) {
      message.error('创建报告失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Title level={3}>快捷操作</Title>
            <div style={{ marginTop: 16 }}>
              <Button
                type="primary"
                size="large"
                icon={<PlusOutlined />}
                onClick={() => setCreateModalVisible(true)}
              >
                生成今日报告
              </Button>
            </div>
          </Card>
        </Col>
        <Col span={24}>
          <Card title="最近报告" loading={loading}>
            {reports.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Text type="secondary">暂无报告</Text>
              </div>
            ) : (
              <List
                dataSource={reports}
                renderItem={(report) => (
                  <List.Item
                    actions={[
                      <Button type="link" onClick={() => navigate(`/reports/${report.id}`)}>
                        查看详情
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<CalendarOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                      title={report.report_date}
                      description={
                        <Text type="secondary">
                          状态: {report.status === 'completed' ? '已完成' :
                                  report.status === 'processing' ? '处理中' :
                                  report.status === 'error' ? '错误' : '待处理'}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="创建报告"
        open={createModalVisible}
        onOk={handleCreateReport}
        onCancel={() => setCreateModalVisible(false)}
        confirmLoading={loading}
      >
        <div style={{ marginBottom: 16 }}>
          <Text>选择报告日期：</Text>
        </div>
        <DatePicker
          value={selectedDate}
          onChange={(date) => date && setSelectedDate(date)}
          style={{ width: '100%' }}
        />
      </Modal>
    </div>
  );
}
