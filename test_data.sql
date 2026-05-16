-- Test Data for Quiz Execution System
-- Inserts 20 questions, 2 quizzes, and assigns to Alice (user_id=1)
-- Usage: Run this to reset quiz system with clean test data

-- Clean up existing data
DELETE FROM prod.quiz_execution;
DELETE FROM prod.user_quiz;
DELETE FROM prod.quiz;
DELETE FROM prod.q_bank;

-- Insert 20 questions (5 MCQ, 5 MR, 5 FILL, 3 OHS, 2 FEVAL)
INSERT INTO prod.q_bank (type, topic, subtopic, level, json, created_at) VALUES
('mcq', 'Algebra', 'Linear', 'B', '{"stem":{"latex":"2x+3=7?"},"input":{"options":["1","2","3","4"]},"output":{"correct_index":2}}', NOW()),
('mcq', 'Algebra', 'Quadratic', 'I', '{"stem":{"latex":"x^2-5x+6=0"},"input":{"options":["2,3","1,6","-2,-3","0,5"]},"output":{"correct_index":0}}', NOW()),
('mcq', 'Geometry', 'Triangles', 'B', '{"stem":{"latex":"Sum angles?"},"input":{"options":["90","180","270","360"]},"output":{"correct_index":1}}', NOW()),
('mcq', 'Number', 'Integers', 'B', '{"stem":{"latex":"Sum to -7"},"input":{"options":["-1,-6","-2,-5","-3,-4","-1,-5"]},"output":{"correct_index":1}}', NOW()),
('mcq', 'Algebra', 'Functions', 'I', '{"stem":{"latex":"f(x)=2x+1"},"input":{"options":["5","6","7","8"]},"output":{"correct_index":2}}', NOW()),
('mr', 'Algebra', 'Properties', 'I', '{"stem":{"latex":"Select"},"input":{"options":["A","B","C","D"]},"output":{"correct_indices":[0,1,2]}}', NOW()),
('mr', 'Geometry', 'Shapes', 'B', '{"stem":{"latex":"Square"},"input":{"options":["A","B","C","D"]},"output":{"correct_indices":[0,1,2]}}', NOW()),
('mr', 'Algebra', 'Inequalities', 'I', '{"stem":{"latex":"x>3"},"input":{"options":["4","3.5","5","2"]},"output":{"correct_indices":[0,1,2]}}', NOW()),
('mr', 'Number', 'Divisible', 'I', '{"stem":{"latex":"By 6"},"input":{"options":["12","18","24","30"]},"output":{"correct_indices":[0,1,2,3]}}', NOW()),
('mr', 'Stats', 'Data', 'B', '{"stem":{"latex":"Tendency"},"input":{"options":["A","B","C","D"]},"output":{"correct_indices":[0,1,2]}}', NOW()),
('fill', 'Algebra', 'Basic', 'B', '{"stem":{"latex":"5+___=12"},"input":{"blanks":[{"id":"b1"}]},"output":{"answers":{"b1":"7"}}}', NOW()),
('fill', 'Geometry', 'Area', 'I', '{"stem":{"latex":"5x3=___"},"input":{"blanks":[{"id":"b1"}]},"output":{"answers":{"b1":"15"}}}', NOW()),
('fill', 'Algebra', 'Exp', 'I', '{"stem":{"latex":"2^3=___"},"input":{"blanks":[{"id":"b1"}]},"output":{"answers":{"b1":"8"}}}', NOW()),
('fill', 'Number', 'Frac', 'B', '{"stem":{"latex":"1/2+1/4=___"},"input":{"blanks":[{"id":"b1"}]},"output":{"answers":{"b1":"3/4"}}}', NOW()),
('fill', 'Algebra', 'Vars', 'B', '{"stem":{"latex":"3x=15"},"input":{"blanks":[{"id":"b1"}]},"output":{"answers":{"b1":"5"}}}', NOW()),
('ohs', 'Geometry', 'Coords', 'I', '{"stem":{"latex":"Click"},"input":{"image":{"src":"/g.png"},"hotspots":[{"x":200,"y":200}]},"output":{"correct_hotspot":0}}', NOW()),
('ohs', 'Geometry', 'Points', 'B', '{"stem":{"latex":"Click"},"input":{"image":{"src":"/g.png"},"hotspots":[{"x":300,"y":100}]},"output":{"correct_hotspot":0}}', NOW()),
('ohs', 'Geometry', 'Shapes', 'I', '{"stem":{"latex":"Click"},"input":{"image":{"src":"/s.png"},"hotspots":[{"x":100,"y":100},{"x":250,"y":250}]},"output":{"correct_hotspot":1}}', NOW()),
('feval', 'Algebra', 'Expr', 'I', '{"stem":{"latex":"2x+3y"},"input":{"variables":[{"name":"x","value":2},{"name":"y","value":1}]},"output":{"correct_answer":"7"}}', NOW()),
('feval', 'Algebra', 'Form', 'I', '{"stem":{"latex":"pir2"},"input":{"variables":[{"name":"r","value":2}]},"output":{"correct_answer":"12.56"}}', NOW());

-- Insert Quiz 1 (questions 1-5)
INSERT INTO prod.quiz (title, description, topic, subtopic, question_ids, question_count, status, created_at, updated_at) 
VALUES ('Quiz 1 Mixed', 'Test with 5 questions', 'Mixed', 'Test', '1,2,3,4,5', 5, 'active', NOW(), NOW());

-- Insert Quiz 2 (questions 6-10)
INSERT INTO prod.quiz (title, description, topic, subtopic, question_ids, question_count, status, created_at, updated_at) 
VALUES ('Quiz 2 Mixed', 'Test with 5 questions', 'Mixed', 'Test', '6,7,8,9,10', 5, 'active', NOW(), NOW());

-- Assign both quizzes to Alice (user_id=1)
INSERT INTO prod.user_quiz (user_id, quiz_id, status, score, responses, created_at, updated_at)
VALUES 
(1, CURRVAL('prod.quiz_id_seq') - 1, 'assigned', 0, '[]', NOW(), NOW()),
(1, CURRVAL('prod.quiz_id_seq'), 'assigned', 0, '[]', NOW(), NOW());

-- Verify everything
SELECT COUNT(*) as total_questions FROM prod.q_bank;
SELECT id, title, question_ids FROM prod.quiz ORDER BY id DESC LIMIT 2;
SELECT id, user_id, quiz_id, status FROM prod.user_quiz WHERE user_id = 1 ORDER BY id DESC LIMIT 2;
