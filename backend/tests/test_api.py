"""接口级测试：覆盖鉴权、志愿、面试、选拔、确认、补录、调剂、公示全链路。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app import models
from app.core.demo import DEMO_PASSWORD


def _register(client, student_no: str, name: str, password: str = DEMO_PASSWORD) -> dict:
    resp = client.post(
        '/auth/register',
        json={'student_no': student_no, 'name': name, 'password': password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['data']


def _admin_token(client) -> str:
    resp = client.post('/auth/login', json={'student_no': 'admin', 'password': DEMO_PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()['data']['access_token']


def _auth(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def admin(client, db_session):
    from app.core.security import hash_password

    user = models.User(
        student_no='admin',
        name='管理员',
        role=models.Role.admin,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def setup_data(client, db_session, admin):
    token = _admin_token(client)
    lab = client.post(
        '/admin/labs',
        json={'name': '人工智能实训室', 'capacity': 2, 'direction': 'AI'},
        headers=_auth(token),
    ).json()['data']

    mentor = client.post(
        '/admin/mentors',
        json={'lab_id': lab['id'], 'name': '张老师', 'quota': 1},
        headers=_auth(token),
    ).json()['data']

    now = datetime.utcnow()
    round_id = client.post(
        '/admin/rounds',
        json={
            'name': '第一轮填报',
            'kind': 'intention',
            'round_no': 1,
            'starts_at': (now - timedelta(days=1)).isoformat(),
            'ends_at': (now + timedelta(days=1)).isoformat(),
        },
        headers=_auth(token),
    ).json()['data']['id']

    return {'token': token, 'lab_id': lab['id'], 'mentor_id': mentor['id'], 'round_id': round_id}


def test_health_and_meta(client):
    assert client.get('/health').json()['code'] == 0
    labs = client.get('/meta/labs').json()
    assert labs['code'] == 0 and labs['data'] == []


def test_register_login_and_me(client):
    data = _register(client, '2024001', '测试学生')
    token = data['access_token']
    me = client.get('/auth/me', headers=_auth(token)).json()
    assert me['data']['student_no'] == '2024001'

    duplicate = client.post(
        '/auth/register',
        json={'student_no': '2024001', 'name': '重复', 'password': DEMO_PASSWORD},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()['code'] == 4001


def test_login_rejects_wrong_password(client):
    _register(client, '2024002', '学生二')
    resp = client.post('/auth/login', json={'student_no': '2024002', 'password': 'wrong-password'})
    assert resp.status_code == 401
    assert resp.json()['code'] == 2001


def test_student_without_token_is_rejected(client):
    """未登录不得访问学生私有数据（DEMO_MODE 需已存在演示账号才回退身份）。"""
    resp = client.get('/student/offers')
    assert resp.status_code == 401
    assert resp.json()['code'] == 2001


def test_intention_requires_student_role(client, setup_data):
    resp = client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(setup_data['token']),
    )
    assert resp.status_code == 403
    assert resp.json()['code'] == 4003


def test_intention_submission_and_replacement(client, setup_data):
    student = _register(client, '2024010', '志愿学生')
    headers = _auth(student['access_token'])

    body = {
        'mentor_ids': [setup_data['mentor_id']],
        'round_id': setup_data['round_id'],
        'obey_internal': True,
        'obey_cross': False,
    }
    resp = client.post('/student/intentions', json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()['data']) == 1

    # 重复提交会覆盖而不是追加
    resp = client.post('/student/intentions', json=body, headers=headers)
    assert len(resp.json()['data']) == 1

    status = client.get('/student/status', headers=headers).json()['data']
    assert status['stage'] == 'applied'
    assert status['obey_internal'] is True


def test_intention_accepts_only_mentors(client, db_session, setup_data):
    """最多 3 个志愿：4 个触发参数校验；3 个合法。"""
    student = _register(client, '2024011', '超额志愿')
    headers = _auth(student['access_token'])

    lab = client.post(
        '/admin/labs',
        json={'name': '大容量实训室', 'capacity': 10},
        headers=_auth(setup_data['token']),
    ).json()['data']

    mentor_ids = []
    for index in range(4):
        created = client.post(
            '/admin/mentors',
            json={'lab_id': lab['id'], 'name': f'导师{index}', 'quota': 2},
            headers=_auth(setup_data['token']),
        ).json()['data']
        mentor_ids.append(created['id'])

    too_many = client.post(
        '/student/intentions',
        json={'mentor_ids': mentor_ids, 'round_id': setup_data['round_id']},
        headers=headers,
    )
    assert too_many.status_code == 422
    assert too_many.json()['code'] == 1001

    ok_resp = client.post(
        '/student/intentions',
        json={'mentor_ids': mentor_ids[:3], 'round_id': setup_data['round_id']},
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert len(ok_resp.json()['data']) == 3


def test_full_selection_flow(client, setup_data):
    token = setup_data['token']
    mentor_id = setup_data['mentor_id']
    round_id = setup_data['round_id']

    s1 = _register(client, '2024020', '高分学生')
    s2 = _register(client, '2024021', '低分学生')

    for student in (s1, s2):
        client.post(
            '/student/intentions',
            json={'mentor_ids': [mentor_id], 'round_id': round_id},
            headers=_auth(student['access_token']),
        )

    # 面试评分：s1 明显高于 s2
    for student, scores in (
        (s1, (25, 20, 35, 20)),
        (s2, (10, 8, 12, 6)),
    ):
        scores_body = dict(
            zip(
                ('score_attitude', 'score_logic', 'score_code', 'score_time'),
                scores,
            )
        )
        resp = client.post(
            '/admin/interviews',
            json={
                'student_id': student['user']['id'],
                'mentor_id': mentor_id,
                'round_id': round_id,
                **scores_body,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text

    run = client.post(
        '/admin/run-selection',
        json={'round_id': round_id, 'confirm_minutes': 60},
        headers=_auth(token),
    )
    assert run.status_code == 200, run.text
    result = run.json()['data']
    assert result['proposed'] == 1
    assert result['offers_created'] == 1

    # 只有高分学生拿到 offer
    offers_high = client.get('/student/offers', headers=_auth(s1['access_token'])).json()['data']
    offers_low = client.get('/student/offers', headers=_auth(s2['access_token'])).json()['data']
    assert len(offers_high) == 1 and offers_high[0]['status'] == 'pending'
    assert offers_low == []

    confirm = client.post(
        '/student/offers/confirm-unique',
        json={'mentor_id': mentor_id},
        headers=_auth(s1['access_token']),
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()['data']['status'] == 'confirmed'

    status = client.get('/student/status', headers=_auth(s1['access_token'])).json()['data']
    assert status['stage'] == 'enrolled'

    # 名额已满，递补失败
    fill = client.post(
        f'/admin/fill-vacancy/{mentor_id}',
        json={'round_id': round_id},
        headers=_auth(token),
    ).json()['data']
    assert fill['filled'] is False


def test_run_selection_is_idempotent(client, setup_data):
    token = setup_data['token']
    student = _register(client, '2024030', '幂等学生')
    client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(student['access_token']),
    )
    client.post(
        '/admin/interviews',
        json={
            'student_id': student['user']['id'],
            'mentor_id': setup_data['mentor_id'],
            'round_id': setup_data['round_id'],
            'score_attitude': 20,
            'score_logic': 15,
            'score_code': 30,
            'score_time': 15,
        },
        headers=_auth(token),
    )

    first = client.post(
        '/admin/run-selection',
        json={'round_id': setup_data['round_id']},
        headers=_auth(token),
    ).json()['data']
    second = client.post(
        '/admin/run-selection',
        json={'round_id': setup_data['round_id']},
        headers=_auth(token),
    ).json()['data']

    assert first['offers_created'] == 1
    assert second['offers_created'] == 0
    assert second['offers_skipped'] >= 1


def test_run_selection_dry_run_creates_nothing(client, setup_data):
    token = setup_data['token']
    student = _register(client, '2024031', '预演学生')
    client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(student['access_token']),
    )
    client.post(
        '/admin/interviews',
        json={
            'student_id': student['user']['id'],
            'mentor_id': setup_data['mentor_id'],
            'round_id': setup_data['round_id'],
            'score_attitude': 18,
            'score_logic': 14,
            'score_code': 26,
            'score_time': 13,
        },
        headers=_auth(token),
    )
    result = client.post(
        '/admin/run-selection',
        json={'round_id': setup_data['round_id'], 'dry_run': True},
        headers=_auth(token),
    ).json()['data']
    assert result['dry_run'] is True
    assert result['proposed'] == 1
    assert client.get('/admin/offers', headers=_auth(token)).json()['data']['total'] == 0


def test_expire_and_fill_vacancy(client, setup_data):
    token = setup_data['token']
    mentor_id = setup_data['mentor_id']
    round_id = setup_data['round_id']

    students = [_register(client, f'202403{i}', f'递补学生{i}') for i in range(2)]
    for student in students:
        client.post(
            '/student/intentions',
            json={'mentor_ids': [mentor_id], 'round_id': round_id},
            headers=_auth(student['access_token']),
        )
        client.post(
            '/admin/interviews',
            json={
                'student_id': student['user']['id'],
                'mentor_id': mentor_id,
                'round_id': round_id,
                'score_attitude': 20,
                'score_logic': 15,
                'score_code': 28,
                'score_time': 14,
            },
            headers=_auth(token),
        )

    client.post('/admin/run-selection', json={'round_id': round_id}, headers=_auth(token))

    # 让 offer 过期（confirm_minutes 最小 1 分钟，这里直接改库）
    offer = client.get('/admin/offers', headers=_auth(token)).json()['data']['items'][0]
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        row = db.get(models.Offer, offer['id'])
        row.expires_at = datetime.utcnow() - timedelta(minutes=5)
        db.commit()
    finally:
        db.close()

    expired = client.post('/admin/expire-offers', headers=_auth(token)).json()['data']
    assert expired['expired'] == 1

    filled = client.post(
        f'/admin/fill-vacancy/{mentor_id}',
        json={'round_id': round_id},
        headers=_auth(token),
    ).json()['data']
    assert filled['filled'] is True
    assert filled['student_id'] in {s['user']['id'] for s in students}


def test_adjust_dry_run_and_assign_talk(client, setup_data):
    token = setup_data['token']
    round_id = setup_data['round_id']

    student = _register(client, '2024040', '调剂学生')
    client.post(
        '/admin/interviews',
        json={
            'student_id': student['user']['id'],
            'mentor_id': setup_data['mentor_id'],
            'round_id': round_id,
            'score_attitude': 15,
            'score_logic': 10,
            'score_code': 20,
            'score_time': 10,
        },
        headers=_auth(token),
    )

    preview = client.post(
        '/admin/adjust',
        json={'round_id': round_id, 'dry_run': True},
        headers=_auth(token),
    ).json()['data']
    # 未服从任何调剂 -> 进入约谈名单
    assert preview['allocations'] == []
    assert [t['student_id'] for t in preview['talk_list']] == [student['user']['id']]

    assigned = client.post(
        '/admin/assign-talk',
        json={
            'student_id': student['user']['id'],
            'mentor_id': setup_data['mentor_id'],
            'round_id': round_id,
            'reason': '约谈后统筹安置',
        },
        headers=_auth(token),
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()['data']['offer_id']

    dashboard = client.get('/admin/dashboard', headers=_auth(token)).json()['data']
    assert dashboard['offers_pending'] == 1
    assert dashboard['quota_left'] == 0


def test_publication_and_appeal(client, setup_data):
    token = setup_data['token']
    student = _register(client, '2024050', '申诉学生')
    headers = _auth(student['access_token'])

    created = client.post(
        '/admin/publications',
        json={'title': '拟录取名单公示', 'content': '公示期 1 天'},
        headers=_auth(token),
    ).json()['data']
    published = client.post(
        f"/admin/publications/{created['id']}/publish", headers=_auth(token)
    )
    assert published.json()['data']['status'] == 'published'

    public = client.get('/publications').json()['data']
    assert len(public) == 1 and public[0]['title'] == '拟录取名单公示'

    appeal = client.post(
        '/student/appeals',
        json={'publication_id': created['id'], 'content': '我的面试分数统计有误，申请复核。'},
        headers=headers,
    )
    assert appeal.status_code == 200, appeal.text
    appeal_id = appeal.json()['data']['id']

    handled = client.post(
        f'/admin/appeals/{appeal_id}/handle',
        json={'status': 'accepted', 'reply': '已复核，分数无误但补录顺位调整。'},
        headers=_auth(token),
    )
    assert handled.json()['data']['status'] == 'accepted'

    mine = client.get('/student/appeals', headers=headers).json()['data']
    assert mine[0]['status'] == 'accepted'


def test_mentor_quota_cannot_exceed_lab_capacity(client, setup_data):
    resp = client.post(
        '/admin/mentors',
        json={'lab_id': setup_data['lab_id'], 'name': '超额导师', 'quota': 5},
        headers=_auth(setup_data['token']),
    )
    assert resp.status_code == 409
    assert resp.json()['code'] == 4001


def test_mentor_quota_cannot_drop_below_taken(client, setup_data):
    token = setup_data['token']
    student = _register(client, '2024060', '占位学生')
    client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(student['access_token']),
    )
    client.post(
        '/admin/interviews',
        json={
            'student_id': student['user']['id'],
            'mentor_id': setup_data['mentor_id'],
            'round_id': setup_data['round_id'],
            'score_attitude': 20,
            'score_logic': 15,
            'score_code': 30,
            'score_time': 15,
        },
        headers=_auth(token),
    )
    client.post('/admin/run-selection', json={'round_id': setup_data['round_id']}, headers=_auth(token))

    resp = client.patch(
        f"/admin/mentors/{setup_data['mentor_id']}",
        json={'quota': 0},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_validation_error_shape(client, setup_data):
    resp = client.post(
        '/admin/interviews',
        json={
            'student_id': 1,
            'mentor_id': setup_data['mentor_id'],
            'round_id': setup_data['round_id'],
            'score_attitude': 99,
            'score_logic': 0,
            'score_code': 0,
            'score_time': 0,
        },
        headers=_auth(setup_data['token']),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body['code'] == 1001
    assert body['data'][0]['loc'][-1] == 'score_attitude'


def test_audit_log_records_actions(client, setup_data):
    student = _register(client, '2024070', '审计学生')
    client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(student['access_token']),
    )
    logs = client.get(
        '/admin/audit-logs', headers=_auth(setup_data['token'])
    ).json()['data']
    actions = {item['action'] for item in logs['items']}
    assert 'submit_intentions' in actions
    assert 'create_lab' in actions


# ---------- 回归：确认截止时间不可由客户端指定 ----------


def test_confirm_ignores_client_supplied_now(client, db_session, setup_data):
    """回归：ConfirmIn 曾暴露 ``now`` 字段，学生可传入早于截止的时间绕过逾期校验。"""
    from datetime import datetime as _dt

    token = setup_data['token']
    mentor_id, round_id = setup_data['mentor_id'], setup_data['round_id']
    student = _register(client, '2024080', '逾期学生')

    client.post(
        '/student/intentions',
        json={'mentor_ids': [mentor_id], 'round_id': round_id},
        headers=_auth(student['access_token']),
    )
    client.post(
        '/admin/interviews',
        json={
            'student_id': db_session.query(models.User)
            .filter(models.User.student_no == '2024080').one().id,
            'mentor_id': mentor_id,
            'round_id': round_id,
            'score_attitude': 25,
            'score_logic': 20,
            'score_code': 35,
            'score_time': 20,
        },
        headers=_auth(token),
    )
    client.post(
        '/admin/run-selection',
        json={'round_id': round_id, 'confirm_minutes': 60},
        headers=_auth(token),
    )
    # 把 offer 置为已逾期
    offer = (
        db_session.query(models.Offer)
        .filter(models.Offer.mentor_id == mentor_id)
        .order_by(models.Offer.id.desc())
        .first()
    )
    offer.expires_at = _dt.utcnow() - timedelta(minutes=5)
    db_session.commit()

    # 客户端带上伪造的 now（早于截止时间）也不应被采信
    resp = client.post(
        '/student/offers/confirm-unique',
        json={'mentor_id': mentor_id, 'now': (offer.expires_at - timedelta(days=1)).isoformat()},
        headers=_auth(student['access_token']),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()['code'] == 3001


def test_confirm_rejects_extra_now_field_ignored_not_500(client, setup_data):
    """即使客户端传 tz-aware 的 now，也不应产生 500（该字段已被移除）。"""
    student = _register(client, '2024081', '时区学生')
    client.post(
        '/student/intentions',
        json={'mentor_ids': [setup_data['mentor_id']], 'round_id': setup_data['round_id']},
        headers=_auth(student['access_token']),
    )
    resp = client.post(
        '/student/offers/confirm-unique',
        json={'mentor_id': setup_data['mentor_id'], 'now': '2030-01-01T00:00:00+00:00'},
        headers=_auth(student['access_token']),
    )
    assert resp.status_code != 500, resp.text
    assert resp.json()['code'] != 5000


# ---------- 回归：轮次 PATCH 支持部分更新 ----------


def test_update_round_is_partial(client, setup_data):
    """回归：update_round 曾用全字段模型覆盖，PATCH 部分字段会重置 kind/round_no。"""
    token = setup_data['token']
    headers = _auth(token)

    created = client.post(
        '/admin/rounds',
        json={
            'name': '面试轮',
            'kind': 'interview',
            'round_no': 3,
            'starts_at': '2026-03-01T08:00:00',
            'ends_at': '2026-03-01T18:00:00',
        },
        headers=headers,
    ).json()['data']['id']

    resp = client.patch(
        f'/admin/rounds/{created}',
        json={'name': '面试轮（改名）'},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    row = next(
        r for r in client.get('/admin/rounds', headers=headers).json()['data']
        if r['id'] == created
    )
    assert row['name'] == '面试轮（改名）'
    assert row['kind'] == 'interview', 'kind 被默认值覆盖了'
    assert row['round_no'] == 3, 'round_no 被默认值覆盖了'


def test_update_round_rejects_inverted_range(client, setup_data):
    headers = _auth(setup_data['token'])
    created = client.post(
        '/admin/rounds',
        json={
            'name': '待改轮',
            'kind': 'confirm',
            'round_no': 2,
            'starts_at': '2026-04-01T08:00:00',
            'ends_at': '2026-04-01T18:00:00',
        },
        headers=headers,
    ).json()['data']['id']

    resp = client.patch(
        f'/admin/rounds/{created}',
        json={'ends_at': '2026-04-01T07:00:00'},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()['code'] == 1001


# ---------- 回归：分页参数边界 ----------


def test_negative_limit_is_rejected(client, setup_data):
    """回归：limit 曾无下界，SQLite 下 limit=-1 等于不分页。"""
    headers = _auth(setup_data['token'])
    for path in ('/admin/offers', '/admin/interviews', '/admin/students', '/admin/audit-logs'):
        resp = client.get(f'{path}?limit=-1', headers=headers)
        assert resp.status_code == 422, f'{path} 未拒绝 limit=-1'
        assert resp.json()['code'] == 1001

    resp = client.get('/auth/users?limit=-1', headers=headers)
    assert resp.status_code == 422
    assert resp.json()['code'] == 1001


def test_negative_offset_is_rejected(client, setup_data):
    headers = _auth(setup_data['token'])
    resp = client.get('/admin/offers?offset=-5', headers=headers)
    assert resp.status_code == 422
    assert resp.json()['code'] == 1001


def test_offer_keyword_filter_applies_before_pagination(client, db_session, setup_data):
    """回归：keyword 曾在分页之后于 Python 中过滤，导致 total 与实际不符。"""
    token = setup_data['token']
    mentor_id, round_id = setup_data['mentor_id'], setup_data['round_id']
    headers = _auth(token)

    for no, name in (('2024091', '关键字甲'), ('2024092', '关键字乙'), ('2024093', '旁人丙')):
        s = _register(client, no, name)
        client.post(
            '/student/intentions',
            json={'mentor_ids': [mentor_id], 'round_id': round_id},
            headers=_auth(s['access_token']),
        )

    # 直接落库 3 条 offer（避免依赖选拔时序）
    ids = {
        u.student_no: u.id
        for u in db_session.query(models.User)
        .filter(models.User.student_no.in_(['2024091', '2024092', '2024093']))
        .all()
    }
    for no, sid in ids.items():
        db_session.add(
            models.Offer(
                student_id=sid,
                mentor_id=mentor_id,
                round_id=round_id,
                offer_type=models.OfferType.regular,
                status=models.OfferStatus.pending,
                reason=f'测试 {no}',
            )
        )
    db_session.commit()

    body = client.get('/admin/offers?keyword=关键字', headers=headers).json()['data']
    assert body['total'] == 2, f"total 应只计匹配项，实际 {body['total']}"
    assert len(body['items']) == 2

    body2 = client.get('/admin/offers?keyword=旁人', headers=headers).json()['data']
    assert body2['total'] == 1
    assert body2['items'][0]['student_no'] == '2024093'
