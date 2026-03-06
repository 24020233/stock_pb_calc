import { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Form, Input, InputNumber, Switch, Space, Popconfirm, message, Modal, Select, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { TargetAccount, StrategyRule } from '@/types';
import { settingsApi } from '@/services/api';

const { TabPane } = Tabs;

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('accounts');
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState<TargetAccount[]>([]);
  const [rules, setRules] = useState<StrategyRule[]>([]);
  const [accountModalVisible, setAccountModalVisible] = useState(false);
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState<TargetAccount | null>(null);
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null);
  const [accountForm] = Form.useForm();
  const [ruleForm] = Form.useForm();

  useEffect(() => {
    if (activeTab === 'accounts') {
      loadAccounts();
    } else if (activeTab === 'rules') {
      loadRules();
    }
  }, [activeTab]);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const res = await settingsApi.listAccounts();
      if (res.data.code === 0) {
        setAccounts(res.data.data?.accounts || []);
      }
    } catch (error) {
      message.error('加载公众号列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadRules = async () => {
    try {
      setLoading(true);
      const res = await settingsApi.listRules();
      if (res.data.code === 0) {
        setRules(res.data.data?.rules || []);
      }
    } catch (error) {
      message.error('加载规则列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAccount = async (values: any) => {
    try {
      setLoading(true);
      if (editingAccount) {
        await settingsApi.updateAccount(editingAccount.id, values);
        message.success('更新公众号成功');
      } else {
        await settingsApi.createAccount(values);
        message.success('添加公众号成功');
      }
      setAccountModalVisible(false);
      accountForm.resetFields();
      loadAccounts();
    } catch (error) {
      message.error('保存公众号失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRule = async (values: any) => {
    try {
      setLoading(true);

      // 解析 rule_value JSON
      let ruleValue = {};
      if (values.rule_value_json) {
        try {
          ruleValue = JSON.parse(values.rule_value_json);
        } catch (e) {
          message.error('规则参数 JSON 格式错误');
          setLoading(false);
          return;
        }
      }

      // 对于旧规则，保留原有的参数处理逻辑
      if (editingRule && !editingRule.rule_handler) {
        const legacyRuleValue = {};
        if (values.min_market_cap !== undefined) legacyRuleValue.min_market_cap = values.min_market_cap;
        if (values.max_market_cap !== undefined) legacyRuleValue.max_market_cap = values.max_market_cap;
        if (values.min_volume_ratio !== undefined) legacyRuleValue.min_volume_ratio = values.min_volume_ratio;
        if (values.min_change_pct !== undefined) legacyRuleValue.min_change_pct = values.min_change_pct;
        if (values.max_change_pct !== undefined) legacyRuleValue.max_change_pct = values.max_change_pct;
        if (values.min_turnover !== undefined) legacyRuleValue.min_turnover = values.min_turnover;
        if (values.max_turnover !== undefined) legacyRuleValue.max_turnover = values.max_turnover;
        if (values.min_pe !== undefined) legacyRuleValue.min_pe = values.min_pe;
        if (values.max_pe !== undefined) legacyRuleValue.max_pe = values.max_pe;
        if (values.min_pb !== undefined) legacyRuleValue.min_pb = values.min_pb;
        if (values.max_pb !== undefined) legacyRuleValue.max_pb = values.max_pb;
        if (values.min_roe !== undefined) legacyRuleValue.min_roe = values.min_roe;
        ruleValue = Object.keys(legacyRuleValue).length > 0 ? legacyRuleValue : ruleValue;
      }

      if (editingRule) {
        // 更新现有规则
        await settingsApi.updateRule(editingRule.rule_key, {
          rule_name: values.rule_name,
          rule_handler: values.rule_handler,
          rule_value: ruleValue,
          description: values.description,
          is_enabled: values.is_enabled,
          sort_order: values.sort_order,
        });
        message.success('更新规则成功');
      } else {
        // 创建新规则
        await settingsApi.createRule({
          rule_key: values.rule_key,
          rule_name: values.rule_name,
          rule_handler: values.rule_handler,
          rule_value: ruleValue,
          description: values.description,
          is_enabled: values.is_enabled ?? true,
          sort_order: values.sort_order ?? 0,
        });
        message.success('创建规则成功');
      }

      setRuleModalVisible(false);
      ruleForm.resetFields();
      setEditingRule(null);
      loadRules();
    } catch (error) {
      message.error('保存规则失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (id: number) => {
    try {
      await settingsApi.deleteAccount(id);
      message.success('删除成功');
      loadAccounts();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleDeleteRule = async (ruleKey: string) => {
    try {
      setLoading(true);
      await settingsApi.deleteRule(ruleKey);
      message.success('删除规则成功');
      loadRules();
    } catch (error) {
      message.error('删除规则失败');
    } finally {
      setLoading(false);
    }
  };

  const accountColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '公众号名称',
      dataIndex: 'account_name',
      key: 'account_name',
    },
    {
      title: '微信号',
      dataIndex: 'wx_id',
      key: 'wx_id',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <span style={{ color: status === 'active' ? '#52c41a' : '#ff4d4f' }}>
          {status === 'active' ? '启用' : '停用'}
        </span>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: TargetAccount) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingAccount(record);
              accountForm.setFieldsValue(record);
              setAccountModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDeleteAccount(record.id)}
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

  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '规则标识',
      dataIndex: 'rule_key',
      key: 'rule_key',
      render: (key: string) => <Tag color="blue">{key}</Tag>,
    },
    {
      title: '处理器识别码',
      dataIndex: 'rule_handler',
      key: 'rule_handler',
      render: (handler: string) => handler ? <Tag color="green">{handler}</Tag> : <span style={{ color: '#999' }}>内置规则</span>,
    },
    {
      title: '是否启用',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 100,
      render: (enabled: boolean) => (
        <span style={{ color: enabled ? '#52c41a' : '#ff4d4f' }}>
          {enabled ? '是' : '否'}
        </span>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: StrategyRule) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingRule(record);
              ruleForm.setFieldsValue({
                rule_key: record.rule_key,
                rule_name: record.rule_name,
                rule_handler: record.rule_handler,
                description: record.description,
                is_enabled: record.is_enabled,
                sort_order: record.sort_order,
                rule_value_json: JSON.stringify(record.rule_value || {}, null, 2),
                ...record.rule_value,
              });
              setRuleModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除此规则?"
            onConfirm={() => handleDeleteRule(record.rule_key)}
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

  // 判断是否为新规则（有 rule_handler）
  const isNewRule = editingRule?.rule_handler || !editingRule;

  return (
    <div>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="公众号配置" key="accounts">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingAccount(null);
                  accountForm.resetFields();
                  setAccountModalVisible(true);
                }}
              >
                添加公众号
              </Button>
            </div>
            <Table
              dataSource={accounts}
              columns={accountColumns}
              rowKey="id"
              loading={loading}
            />
          </TabPane>
          <TabPane tab="选股规则配置" key="rules">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingRule(null);
                  ruleForm.resetFields();
                  ruleForm.setFieldsValue({
                    is_enabled: true,
                    sort_order: 0,
                    rule_value_json: '{}',
                  });
                  setRuleModalVisible(true);
                }}
              >
                新增规则
              </Button>
            </div>
            <Table
              dataSource={rules}
              columns={ruleColumns}
              rowKey="id"
              loading={loading}
            />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title={editingAccount ? '编辑公众号' : '添加公众号'}
        open={accountModalVisible}
        onOk={() => accountForm.submit()}
        onCancel={() => {
          setAccountModalVisible(false);
          accountForm.resetFields();
        }}
        confirmLoading={loading}
      >
        <Form
          form={accountForm}
          onFinish={handleSaveAccount}
          layout="vertical"
        >
          <Form.Item
            name="account_name"
            label="公众号名称"
            rules={[{ required: true, message: '请输入公众号名称' }]}
          >
            <Input placeholder="请输入公众号名称" />
          </Form.Item>
          <Form.Item name="wx_id" label="微信号">
            <Input placeholder="请输入微信号" />
          </Form.Item>
          <Form.Item
            name="status"
            label="状态"
            initialValue="active"
          >
            <Select>
              <Select.Option value="active">启用</Select.Option>
              <Select.Option value="inactive">停用</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="sort_order"
            label="排序"
            initialValue={0}
          >
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRule ? '编辑规则' : '新增规则'}
        open={ruleModalVisible}
        onOk={() => ruleForm.submit()}
        onCancel={() => {
          setRuleModalVisible(false);
          ruleForm.resetFields();
          setEditingRule(null);
        }}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={ruleForm}
          onFinish={handleSaveRule}
          layout="vertical"
        >
          {/* 新增规则时显示 rule_key */}
          {!editingRule && (
            <Form.Item
              name="rule_key"
              label="规则标识"
              rules={[{ required: true, message: '请输入规则标识' }]}
            >
              <Input placeholder="如：continuous_rise_filter" />
            </Form.Item>
          )}

          <Form.Item
            name="rule_name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="如：连续上涨筛选" />
          </Form.Item>

          <Form.Item
            name="rule_handler"
            label="处理器识别码"
            extra="填写后端注册的规则处理器标识，如：continuous_rise"
          >
            <Input placeholder="如：continuous_rise" />
          </Form.Item>

          <Form.Item
            name="rule_value_json"
            label="规则参数 (JSON)"
            extra='JSON 格式的参数，如：{"min_rise_days": 3}'
          >
            <Input.TextArea
              rows={4}
              placeholder='{"min_rise_days": 3}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="规则描述" />
          </Form.Item>

          <Form.Item name="is_enabled" label="是否启用" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          {/* 旧规则的专用参数字段 */}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'market_cap' && (
            <>
              <Form.Item name="min_market_cap" label="最小市值(亿)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="max_market_cap" label="最大市值(亿)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'volume_ratio' && (
            <Form.Item name="min_volume_ratio" label="最小量比">
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'price_change' && (
            <>
              <Form.Item name="min_change_pct" label="最小涨跌幅(%)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="max_change_pct" label="最大涨跌幅(%)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'turnover_rate' && (
            <>
              <Form.Item name="min_turnover" label="最小换手率(%)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="max_turnover" label="最大换手率(%)">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'pe_ratio' && (
            <>
              <Form.Item name="min_pe" label="最小市盈率">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="max_pe" label="最大市盈率">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'pb_ratio' && (
            <>
              <Form.Item name="min_pb" label="最小市净率">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="max_pb" label="最大市净率">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}
          {editingRule && !editingRule.rule_handler && editingRule.rule_key === 'roe' && (
            <Form.Item name="min_roe" label="最小ROE(%)">
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}