INSERT INTO restaurants (id, name)
VALUES (1, 'SmartFlow Demo Restaurant')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO branches (id, restaurant_id, name, address, active)
VALUES (1, 1, 'Main Branch', '123 Market Street', true)
ON CONFLICT (id) DO UPDATE
SET restaurant_id = EXCLUDED.restaurant_id,
    name = EXCLUDED.name,
    address = EXCLUDED.address,
    active = EXCLUDED.active;

INSERT INTO staff_users (branch_id, email, password_hash, role, full_name, active)
VALUES
    (
        1,
        'kitchen@smartflow.local',
        '$2b$12$ASoCK8hdTofzwWK8TKl/QufEluC3nKci/QwH5nIqarxQ.eCpEoCmK',
        'kitchen',
        'Demo Kitchen',
        true
    ),
    (
        1,
        'admin@smartflow.local',
        '$2b$12$ASoCK8hdTofzwWK8TKl/QufEluC3nKci/QwH5nIqarxQ.eCpEoCmK',
        'admin',
        'Demo Admin',
        true
    )
ON CONFLICT (email) DO UPDATE
SET branch_id = EXCLUDED.branch_id,
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    full_name = EXCLUDED.full_name,
    active = EXCLUDED.active;

INSERT INTO dining_tables (id, branch_id, table_code, label, active, qr_image_url)
VALUES
    (1, 1, 'T-12-B', 'Table 12B', true, 'https://cdn.example.com/qr/T-12-B.png'),
    (2, 1, 'T-01', 'Table 1', true, 'https://cdn.example.com/qr/T-01.png'),
    (3, 1, 'T-02', 'Table 2', true, 'https://cdn.example.com/qr/T-02.png')
ON CONFLICT (table_code) DO UPDATE
SET branch_id = EXCLUDED.branch_id,
    label = EXCLUDED.label,
    active = EXCLUDED.active,
    qr_image_url = EXCLUDED.qr_image_url;

INSERT INTO menu_categories (id, branch_id, name, description, image_url, sort_order, active)
VALUES
    (1, 1, 'Main Dishes', 'Freshly prepared house favorites', 'https://cdn.example.com/menu/categories/main-dishes.jpg', 0, true),
    (2, 1, 'Drinks', 'Cold and hot drinks', 'https://cdn.example.com/menu/categories/drinks.jpg', 1, true)
ON CONFLICT (id) DO UPDATE
SET branch_id = EXCLUDED.branch_id,
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    image_url = EXCLUDED.image_url,
    sort_order = EXCLUDED.sort_order,
    active = EXCLUDED.active;

INSERT INTO menu_items
    (id, category_id, branch_id, name, description, price, image_url, thumbnail_url, available, sort_order)
VALUES
    (
        '11111111-1111-4111-8111-111111111111',
        1,
        1,
        'Qozon Osh',
        'Rice pilaf with beef, carrots, chickpeas, and spices',
        45000.00,
        'https://cdn.example.com/menu/items/qozon-osh.jpg',
        'https://cdn.example.com/menu/items/thumbs/qozon-osh.jpg',
        true,
        0
    ),
    (
        '22222222-2222-4222-8222-222222222222',
        1,
        1,
        'Lagman',
        'Hand-pulled noodles with beef and vegetables',
        38000.00,
        'https://cdn.example.com/menu/items/lagman.jpg',
        'https://cdn.example.com/menu/items/thumbs/lagman.jpg',
        true,
        1
    ),
    (
        '33333333-3333-4333-8333-333333333333',
        1,
        1,
        'Manti',
        'Steamed dumplings with seasoned beef filling',
        32000.00,
        'https://cdn.example.com/menu/items/manti.jpg',
        'https://cdn.example.com/menu/items/thumbs/manti.jpg',
        true,
        2
    ),
    (
        '44444444-4444-4444-8444-444444444444',
        2,
        1,
        'Green Tea',
        'Freshly brewed green tea',
        8000.00,
        'https://cdn.example.com/menu/items/green-tea.jpg',
        'https://cdn.example.com/menu/items/thumbs/green-tea.jpg',
        true,
        0
    ),
    (
        '55555555-5555-4555-8555-555555555555',
        2,
        1,
        'Ayran',
        'Chilled yogurt drink with salt',
        12000.00,
        'https://cdn.example.com/menu/items/ayran.jpg',
        'https://cdn.example.com/menu/items/thumbs/ayran.jpg',
        true,
        1
    ),
    (
        '66666666-6666-4666-8666-666666666666',
        2,
        1,
        'Still Water',
        'Bottled still water',
        6000.00,
        'https://cdn.example.com/menu/items/still-water.jpg',
        'https://cdn.example.com/menu/items/thumbs/still-water.jpg',
        true,
        2
    )
ON CONFLICT (id) DO UPDATE
SET category_id = EXCLUDED.category_id,
    branch_id = EXCLUDED.branch_id,
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    image_url = EXCLUDED.image_url,
    thumbnail_url = EXCLUDED.thumbnail_url,
    available = EXCLUDED.available,
    sort_order = EXCLUDED.sort_order,
    updated_at = now();

SELECT setval('restaurants_id_seq', (SELECT max(id) FROM restaurants), true);
SELECT setval('branches_id_seq', (SELECT max(id) FROM branches), true);
SELECT setval('dining_tables_id_seq', (SELECT max(id) FROM dining_tables), true);
SELECT setval('menu_categories_id_seq', (SELECT max(id) FROM menu_categories), true);
