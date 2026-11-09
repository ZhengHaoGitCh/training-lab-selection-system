"""老师端接口测试：权限隔离、只看/只评自己的学生、评分留痕。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app import models
from app.core.demo import DEMO_PASSWORD
from app.core.security import hash_password


def _auth(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


def _login(client, student_no: str) -> str:
    resp = client.post(
        '/auth/login',
        json={'student_no': student_no, 'password': DEMO_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['data']['access_token']


def _register(client, student_no: str, name: str) -> dict:
    resp = client.post(
        '/auth/register',
        json={'student_no': student_no, 'name': name, 'password': DEMO_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['data']


@pytest.fixture()
def setup_data(client, db_session):
    admin = models.User(
        student_no='admin',
        name='管理员',
        role=models.Role.admin,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    db_session.add(admin)
    db_session.commit()

    admin_token = _login(client, 'admin')
    lab = client.post(
        '/admin/labs',
        json={'name': '人工智能实训室', 'capacity': 4, 'direction': 'AI'},
        headers=_auth(admin_token),
    ).json()['data']
    mentor = client.post(
        '/admin/mentors',
        json={'lab_id': lab['id'], 'name': '张老师', 'quota': 2},
        headers=_auth(admin_token),
    ).json()['data']
    other_mentor = client.post(
        '/admin/mentors',
        json={'lab_id': lab['id'], 'name': '李老师', 'quota': 2},
        headers=_auth(admin_token),
    ).json()['data']

    now = datetime.utcnow()

    def create_round(name: str, kind: str, round_no: int) -> int:
        return client.post(
            '/admin/rounds',
            json={
                'name': name,
                'kind': kind,
                'round_no': round_no,
                'starts_at': (now - timedelta(days=1)).isoformat(),
                'ends_at': (now + timedelta(days=2)).isoformat(),
            },
            headers=_auth(admin_token),
        ).json()['data']['id']

    intention_round = create_round('第一轮填报', 'intention', 1)
    interview_round = create_round('第一轮面试', 'interview', 2)

    teacher = models.User(
        student_no='t1001',
        name='张老师',
        role=models.Role.mentor,
        password_hash=hash_password(DEMO_PASSWORD),
        lab_id=lab['id'],
        mentor_id=mentor['id'],
    )
    other_teacher = models.User(
        student_no='t1002',
        name='李老师',
        role=models.Role.mentor,
        password_hash=hash_password(DEMO_PASSWORD),
        lab_id=lab['id'],
        mentor_id=other_mentor['id'],
    )
    db_session.add_all([teacher, other_teacher])
    db_session.commit()

    student = _register(client, '2023001', '陈子墨')
    _register(client, '2023002', '林可欣')

    resp = client.post(
        '/student/intentions',
        json={
            'mentor_ids': [mentor['id']],
            'round_id': intention_round,
            'obey_internal': True,
            'obey_cross': False,
        },
        headers=_auth(student['access_token']),
    )
    assert resp.status_code == 200, resp.text

    return {
        'admin_token': admin_token,
        'teacher_token': _login(client, 't1001'),
        'other_teacher_token': _login(client, 't1002'),
        'student_token': student['access_token'],
        'student_id': student['user']['id'],
        'mentor_id': mentor['id'],
        'other_mentor_id': other_mentor['id'],
        'intention_round': intention_round,
        'interview_round': interview_round,
    }


def test_teacher_profile_and_applicants_are_scoped(client, setup_data):
    teacher_token = setup_data['teacher_token']

    profile = client.get('/teacher/profile', headers=_auth(teacher_token)).json()
    assert profile['code'] == 0
    assert profile['data']['mentor']['id'] == setup_data['mentor_id']
    assert profile['data']['counts']['applicants'] == 1

    applicants = client.get('/teacher/applicants', headers=_auth(teacher_token)).json()['data']
    assert len(applicants) == 1
    assert applicants[0]['student_no'] == '2023001'
    assert applicants[0]['obey_internal'] is True
    assert applicants[0]['interview'] is None

    other = client.get(
        '/teacher/applicants', headers=_auth(setup_data['other_teacher_token'])
    ).json()['data']
    assert other == []


def test_teacher_can_only_score_own_applicants(client, setup_data):
    teacher_token = setup_data['teacher_token']
    payload = {
        'student_id': setup_data['student_id'],
        'round_id': setup_data['interview_round'],
        'score_attitude': 22,
        'score_logic': 18,
        'score_code': 30,
        'score_time': 16,
        'remark': '基础扎实',
    }
    resp = client.post('/teacher/interviews', json=payload, headers=_auth(teacher_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()['data']['total'] == 86

    applicants = client.get('/teacher/applicants', headers=_auth(teacher_token)).json()['data']
    assert applicants[0]['interview']['total_score'] == 86
    assert applicants[0]['interview']['decision'] == 'rejected'

    interviews = client.get(
        '/teacher/interviews',
        params={'round_id': setup_data['interview_round']},
        headers=_auth(teacher_token),
    ).json()['data']
    assert len(interviews) == 1
    assert interviews[0]['student_no'] == '2023001'

    audit = client.get(
        '/admin/audit-logs',
        params={'action': 'create_interview'},
        headers=_auth(setup_data['admin_token']),
    ).json()['data']
    assert audit['total'] == 1
    assert audit['items'][0]['actor'] == 't1001'


def test_teacher_cannot_score_students_outside_own_intentions(client, setup_data):
    payload = {
        'student_id': setup_data['student_id'],
        'round_id': setup_data['interview_round'],
        'score_attitude': 10,
        'score_logic': 10,
        'score_code': 10,
        'score_time': 10,
    }
    resp = client.post(
        '/teacher/interviews',
        json=payload,
        headers=_auth(setup_data['other_teacher_token']),
    )
    assert resp.status_code == 403
    assert resp.json()['code'] == 4003


def test_role_isolation_and_demo_login(client, setup_data):
    student_token = setup_data['student_token']
    resp = client.get('/teacher/profile', headers=_auth(student_token))
    assert resp.status_code == 403

    resp = client.post(
        '/admin/run-selection',
        json={'round_id': setup_data['interview_round']},
        headers=_auth(setup_data['teacher_token']),
    )
    assert resp.status_code == 403

    demo = client.post('/auth/login-demo').json()['data']
    assert demo['teacher']['user']['role'] == 'mentor'
    assert demo['admin']['user']['role'] == 'admin'
    assert demo['student']['user']['role'] == 'student'
