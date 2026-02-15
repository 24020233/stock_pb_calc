import { useState, useEffect } from 'react';
import { Card, Table, Button, Tag, Space, Popconfirm, message, Modal, DatePicker } from 'antd';
import { EyeOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Report } from '@/types';
import { reportsApi } from '@/services/api';
import dayjs from 'dayjs';

export default function ReportsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setLoading(true);
      const res = await reportsApi.list({ limit: 100 });
      if (res.data.code === 0) {
        setReports(res.data.data?.reports || []);
      }
    } catch (error) {
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await reportsApi.delete(id);
      if (res.data.code === 0) {
        message.success('删除成功');
        loadReports();
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleCreateReport = async () => {
    try {
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
          loadReports();
        }
      }
    } catch (error) {
      message.error('创建报告失败');
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      error: { color: 'error', text: '错误' },
    };
    const config = statusMap[status] || statusMap.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '报告日期',
      dataIndex: 'report_date',
      key: 'report_date',
      width: 150,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: Report) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/reports/${record.id}`)}
          >
            查看
          </Button>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="报告管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建报告
          </Button>
        }
      >
        <Table
          dataSource={reports}
          columns={columns}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title="创建报告"
        open={createModalVisible}
        onOk={handleCreateReport}
        onCancel={() => setCreateModalVisible(false)}
      >
        <div style={{ marginBottom: 16 }}>
          选择报告日期：
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
