"""Regression checks for evidence feedback; no API or key required."""
import unittest

from agent import run_agent
from test_lab import FakeProvider, final, tool_call


class MemoryTools:
    def execute(self, name, args):
        if name == 'get_status':
            if args['provider'] == 'cloudflare':
                return {'ok': False, 'error': 'TimeoutError'}
            return {'provider': 'github', 'incidents': [],
                    'note': 'Chỉ tìm trong 50 incident; không tìm thấy không chứng minh không có.'}
        incident = args['incident_id']
        return {'ok': True, 'provider': 'github', 'url': 'https://example.org/' + incident,
                'updates': [{'body': 'https://www.githubstatus.com/incidents/linked'}]
                if incident == 'first' else []}


class AgentRegressions(unittest.TestCase):
    def test_timestamp_without_word_snapshot_is_accepted(self):
        class TimestampTools(MemoryTools):
            def execute(self, name, args):
                result = super().execute(name, args)
                result['captured_at'] = '2026-11-09T03:50:47+00:00'
                return result

        fake = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"github"}'),
            final('GitHub operational. Dữ liệu thu thập ngày 2026-11-09.'),
        ])
        result = run_agent('GitHub hiện có lỗi không?', fake, TimestampTools())
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(e['event'].startswith('validation') for e in result['trace']))

    def test_missing_incident_does_not_invalidate_successful_status(self):
        class MissingIncidentTools(MemoryTools):
            def execute(self, name, args):
                if name == 'get_incident_details':
                    return {'ok': False, 'error': 'INCIDENT_NOT_FOUND'}
                return super().execute(name, args)

        calls = tool_call('a', 'get_status', '{"provider":"github"}')
        other = tool_call('b', 'get_incident_details', '{"provider":"github","incident_id":"missing"}')
        calls['calls'] += other['calls']
        calls['message']['tool_calls'] += other['message']['tool_calls']
        fake = FakeProvider([calls, final('GitHub: operational. Incident không tìm thấy.')])
        result = run_agent('Kiểm tra GitHub.', fake, MissingIncidentTools())
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(e['event'] == 'validation_evidence' for e in result['trace']))

    def test_revision_keeps_successful_provider(self):
        calls = tool_call('a', 'get_status', '{"provider":"github"}')
        other = tool_call('b', 'get_status', '{"provider":"cloudflare"}')
        calls['calls'] += other['calls']
        calls['message']['tool_calls'] += other['message']['tool_calls']
        fake = FakeProvider([
            calls, final('Cloudflare: không thể kiểm tra do timeout.'),
            final('GitHub: operational. Cloudflare: không thể kiểm tra do timeout.'),
        ])
        result = run_agent('Kiểm tra GitHub và Cloudflare.', fake, MemoryTools())
        self.assertEqual(result['status'], 'completed')
        self.assertIn('GitHub', result['answer'])
        self.assertIn('Snapshot status đã lấy được', fake.histories[2][-1]['content'])

    def test_success_without_ok_still_requires_history_boundary(self):
        fake = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"github"}'),
            final('Không có incident trong năm yêu cầu.'),
            final('Không thể xác nhận đầy đủ: tool chỉ có 50 incident gần nhất.'),
        ])
        result = run_agent('Liệt kê đầy đủ lịch sử.', fake, MemoryTools())
        self.assertIn('Không thể xác nhận', result['answer'])

    def test_follow_link_before_final(self):
        fake = FakeProvider([
            tool_call('a', 'get_incident_details', '{"provider":"github","incident_id":"first"}'),
            final('Summary https://example.org/first'),
            tool_call('b', 'get_incident_details', '{"provider":"github","incident_id":"linked"}'),
            final('Summary https://example.org/first https://example.org/linked'),
        ])
        result = run_agent('Theo liên kết tìm nguyên nhân.', fake, MemoryTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len([e for e in result['trace'] if e['event'] == 'tool']), 2)

    def test_missing_source_feedback_contains_exact_url(self):
        fake = FakeProvider([
            tool_call('a', 'get_incident_details', '{"provider":"github","incident_id":"other"}'),
            final('Summary'), final('Summary https://example.org/other'),
        ])
        run_agent('Tóm tắt.', fake, MemoryTools())
        self.assertIn('https://example.org/other', fake.histories[2][-1]['content'])

    def test_timeout_under_heading_cannot_be_operational(self):
        fake = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"cloudflare"}'),
            final('Cloudflare:\nTrạng thái: Đang hoạt động.'),
            final('Cloudflare: không thể xác minh do timeout.'),
        ])
        result = run_agent('Kiểm tra Cloudflare.', fake, MemoryTools())
        self.assertIn('không thể xác minh', result['answer'])

    def test_non_object_arguments_are_invalid_arguments(self):
        fake = FakeProvider([tool_call('a', 'get_status', '[]'), final('Không đủ dữ liệu.')])
        result = run_agent('Kiểm tra.', fake, MemoryTools())
        event = next(e for e in result['trace'] if e['event'] == 'tool')
        self.assertEqual(event['result']['error'], 'INVALID_ARGUMENTS')


if __name__ == '__main__':
    unittest.main()
