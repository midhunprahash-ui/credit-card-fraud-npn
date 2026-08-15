-- Keep analyst workflow actions explicit and auditable. The initial schema did
-- not include closing an alert after investigation.

alter table public.analyst_actions
    drop constraint analyst_actions_action_check;

alter table public.analyst_actions
    add constraint analyst_actions_action_check check (
        action in (
            'OPENED',
            'ASSIGNED',
            'CONFIRMED_FRAUD',
            'MARKED_LEGITIMATE',
            'ESCALATED',
            'NOTE_ADDED',
            'CLOSED'
        )
    );
