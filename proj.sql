
CREATE DATABASE voting_system;
USE voting_system;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE elections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    photo_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

CREATE TABLE votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    election_id INT,
    candidate_id INT,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE KEY unique_vote (user_id, election_id)
);

INSERT INTO users(username,password,email) VALUES ('Dan','123','de@gmail.com');
INSERT INTO users(username,password,email) VALUES ('Sane','123','se@gmail.com');

SELECT * FROM votes WHERE election_id=1;
SELECT * FROM users WHERE is_admin=1;

UPDATE candidates SET description = 'Leader with a focus on transparency and growth' WHERE name = 'Jane Doe';

update users set password='123' where username='user2';
update elections set is_active='0' where id=6;

delete from users where username='user1';

-- TRIGGERS

DELIMITER $$
CREATE TRIGGER prevent_multiple_votes_per_candidate
BEFORE INSERT ON votes
FOR EACH ROW
BEGIN
    DECLARE vote_count INT;
    SELECT COUNT(*) INTO vote_count
    FROM votes
    WHERE user_id = NEW.user_id
      AND candidate_id = NEW.candidate_id;

    IF vote_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User has already voted for this candidate.';
    END IF;
END;

DELIMITER $$

CREATE TRIGGER deactivate_expired_elections
BEFORE UPDATE ON elections
FOR EACH ROW
BEGIN
    IF NEW.end_date < NOW() THEN
        SET NEW.is_active = FALSE;
    END IF;
END$$

DELIMITER $$

CREATE TRIGGER validate_candidate_for_vote
BEFORE INSERT ON votes
FOR EACH ROW
BEGIN
    DECLARE election_id_for_candidate INT;
    SELECT election_id INTO election_id_for_candidate
    FROM candidates
    WHERE id = NEW.candidate_id;

    IF election_id_for_candidate != NEW.election_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Candidate does not belong to the specified election';
    END IF;
END$$

DELIMITER ;

-- PROCEDURES 

use voting_system;
DELIMITER //
CREATE PROCEDURE RegisterUser(
    IN p_username VARCHAR(50),
    IN p_password VARCHAR(255),
    IN p_email VARCHAR(100)
)
BEGIN
    DECLARE user_exists INT;
    -- Check if the username already exists
    SELECT COUNT(*) INTO user_exists
    FROM users
    WHERE username = p_username;
    IF user_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Username already exists';
    ELSE
        -- Insert the new user
        INSERT INTO users (username, password, email)
        VALUES (p_username, p_password, p_email);
    END IF;
END //
DELIMITER ;
DELIMITER //


CREATE PROCEDURE CreateElection(
    IN p_title VARCHAR(255),
    IN p_description TEXT,
    IN p_start_date DATETIME,
    IN p_end_date DATETIME
)
BEGIN
    -- Insert a new election
    INSERT INTO elections (title, description, start_date, end_date, is_active)
    VALUES (p_title, p_description, p_start_date, p_end_date, TRUE);
END //
DELIMITER ;


DELIMITER //
CREATE PROCEDURE AddCandidate(
    IN p_election_id INT,
    IN p_name VARCHAR(100),
    IN p_description TEXT
)
BEGIN
    -- Check if the election exists
    IF EXISTS (SELECT id FROM elections WHERE id = p_election_id) THEN
        -- Insert the candidate
        INSERT INTO candidates (election_id, name, description)
        VALUES (p_election_id, p_name, p_description);
    ELSE
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Election not found';
    END IF;
END //
DELIMITER ;

 DROP PROCEDURE IF EXISTS CastVote;

DELIMITER //
CREATE PROCEDURE CastVote(
    IN p_user_id INT,
    IN p_election_id INT,
    IN p_candidate_id INT
)
BEGIN
    DECLARE election_active INT;
    DECLARE vote_exists INT;

    -- Check if the election is active
    SELECT COUNT(*) INTO election_active
    FROM elections
    WHERE id = p_election_id AND is_active = TRUE AND NOW() < end_date;

    IF election_active = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Election is not active or has ended';
    ELSE
        -- Check if the user has already voted
        SELECT COUNT(*) INTO vote_exists
        FROM votes
        WHERE user_id = p_user_id AND election_id = p_election_id;

        IF vote_exists > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'User has already voted in this election';
        ELSE
            -- Insert the vote
            INSERT INTO votes (user_id, election_id, candidate_id)
            VALUES (p_user_id, p_election_id, p_candidate_id);
        END IF;
    END IF;
END //
DELIMITER ;


select username , email
from users
where id in (select user_id from votes);

select election_id , name
from candidates
where election_id in(
select election_id from votes where election_id=1);

select u.username, c.name from
votes v join users on v.user_id=u.id
join candidates c on v.user_id=c.id;

select candidate_id , count(*) as total_votes
from votes
group by candidate_id;



















