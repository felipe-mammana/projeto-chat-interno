-- Banco de exemplo com dados ficticios para desenvolvimento local.
-- Importacao sugerida:
-- mysql -u root -p < database/fake_seed.sql

CREATE DATABASE IF NOT EXISTS clinica
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE clinica;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS cnn_duplos;
DROP VIEW IF EXISTS procedimento_duplo_itens;
DROP TABLE IF EXISTS chatbot_base_setor;
DROP TABLE IF EXISTS agenda_atendimento;
DROP TABLE IF EXISTS agenda_medico;
DROP TABLE IF EXISTS cnn_dupla_procedimento;
DROP TABLE IF EXISTS medico_procedimento;
DROP TABLE IF EXISTS medico_regras;
DROP TABLE IF EXISTS logins;
DROP TABLE IF EXISTS funcionarios;
DROP TABLE IF EXISTS setores;
DROP TABLE IF EXISTS tipos_atendimento;
DROP TABLE IF EXISTS procedimentos;
DROP TABLE IF EXISTS cnn_dupla;
DROP TABLE IF EXISTS medicos;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE setores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE funcionarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(160) NOT NULL,
  email VARCHAR(180) NULL,
  ramal VARCHAR(30) NULL,
  setor_id INT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_funcionarios_setor
    FOREIGN KEY (setor_id) REFERENCES setores(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE logins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  funcionario_id INT NULL,
  usuario VARCHAR(80) NOT NULL UNIQUE,
  senha VARCHAR(255) NOT NULL,
  nivel ENUM('usuario', 'gerente', 'admin') NOT NULL DEFAULT 'usuario',
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_logins_funcionario
    FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE medicos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(160) NOT NULL,
  crm VARCHAR(40) NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE medico_regras (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medico_id INT NOT NULL UNIQUE,
  imc_geral DECIMAL(5,2) NULL,
  imc_mama_redutora DECIMAL(5,2) NULL,
  imc_pos_bariatrica DECIMAL(5,2) NULL,
  max_cirurgias_combinadas INT NULL,
  indicacao_cirurgica TINYINT(1) NOT NULL DEFAULT 0,
  observacoes TEXT NULL,
  CONSTRAINT fk_medico_regras_medico
    FOREIGN KEY (medico_id) REFERENCES medicos(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE procedimentos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(180) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE medico_procedimento (
  medico_id INT NOT NULL,
  procedimento_id INT NOT NULL,
  PRIMARY KEY (medico_id, procedimento_id),
  CONSTRAINT fk_medico_procedimento_medico
    FOREIGN KEY (medico_id) REFERENCES medicos(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_medico_procedimento_procedimento
    FOREIGN KEY (procedimento_id) REFERENCES procedimentos(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE tipos_atendimento (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE agenda_medico (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medico_id INT NOT NULL,
  dia_semana ENUM('Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta', 'Sabado', 'Domingo') NOT NULL,
  hora_inicio TIME NOT NULL,
  hora_fim TIME NOT NULL,
  CONSTRAINT fk_agenda_medico_medico
    FOREIGN KEY (medico_id) REFERENCES medicos(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE agenda_atendimento (
  agenda_id INT NOT NULL,
  atendimento_id INT NOT NULL,
  PRIMARY KEY (agenda_id, atendimento_id),
  CONSTRAINT fk_agenda_atendimento_agenda
    FOREIGN KEY (agenda_id) REFERENCES agenda_medico(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_agenda_atendimento_tipo
    FOREIGN KEY (atendimento_id) REFERENCES tipos_atendimento(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cnn_dupla (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo_cnn VARCHAR(40) NOT NULL UNIQUE,
  nome VARCHAR(180) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cnn_dupla_procedimento (
  cnn_dupla_id INT NOT NULL,
  procedimento_id INT NOT NULL,
  PRIMARY KEY (cnn_dupla_id, procedimento_id),
  CONSTRAINT fk_cnn_dupla_procedimento_dupla
    FOREIGN KEY (cnn_dupla_id) REFERENCES cnn_dupla(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_cnn_dupla_procedimento_procedimento
    FOREIGN KEY (procedimento_id) REFERENCES procedimentos(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chatbot_base_setor (
  id INT AUTO_INCREMENT PRIMARY KEY,
  id_setor INT NOT NULL,
  pergunta VARCHAR(255) NOT NULL,
  palavras_chave VARCHAR(255) NULL,
  resposta TEXT NOT NULL,
  CONSTRAINT fk_chatbot_base_setor
    FOREIGN KEY (id_setor) REFERENCES setores(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO setores (id, nome) VALUES
  (1, 'Recepcao'),
  (2, 'Financeiro'),
  (3, 'Agendamento'),
  (4, 'Centro Cirurgico');

INSERT INTO funcionarios (id, nome, email, ramal, setor_id, ativo) VALUES
  (1, 'Ana Exemplo', 'ana.exemplo@clinica.test', '201', 1, 1),
  (2, 'Bruno Ficticio', 'bruno.ficticio@clinica.test', '305', 2, 1),
  (3, 'Carla Demo', 'carla.demo@clinica.test', '410', 3, 1),
  (4, 'Diego Teste', 'diego.teste@clinica.test', '512', 4, 0);

INSERT INTO logins (id, funcionario_id, usuario, senha, nivel, ativo) VALUES
  (1, 1, 'admin', '$2b$12$vw7fTqLnAwOdcK2YImAP0e957WXxnPkQOA7f/rPKwk8oYI43r6snW', 'admin', 1),
  (2, 2, 'financeiro', '$2b$12$vw7fTqLnAwOdcK2YImAP0e957WXxnPkQOA7f/rPKwk8oYI43r6snW', 'usuario', 1);

INSERT INTO medicos (id, nome, crm, ativo) VALUES
  (1, 'Dra. Marina Exemplo', 'CRM-TESTE-1001', 1),
  (2, 'Dr. Rafael Modelo', 'CRM-TESTE-1002', 1),
  (3, 'Dra. Julia Demonstracao', 'CRM-TESTE-1003', 0);

INSERT INTO medico_regras
  (medico_id, imc_geral, imc_mama_redutora, imc_pos_bariatrica, max_cirurgias_combinadas, indicacao_cirurgica, observacoes)
VALUES
  (1, 30.00, 28.00, 32.00, 2, 1, 'Dados ficticios para ambiente de desenvolvimento.'),
  (2, 29.50, 27.50, 31.00, 1, 0, 'Avaliacao individual conforme protocolo interno de teste.');

INSERT INTO procedimentos (id, nome) VALUES
  (1, 'Consulta inicial'),
  (2, 'Retorno pos-operatorio'),
  (3, 'Mamoplastia redutora'),
  (4, 'Abdominoplastia'),
  (5, 'Lipoaspiracao');

INSERT INTO medico_procedimento (medico_id, procedimento_id) VALUES
  (1, 1), (1, 2), (1, 3), (1, 5),
  (2, 1), (2, 2), (2, 4);

INSERT INTO tipos_atendimento (id, nome) VALUES
  (1, 'Consulta'),
  (2, 'Retorno'),
  (3, 'Teleatendimento');

INSERT INTO agenda_medico (id, medico_id, dia_semana, hora_inicio, hora_fim) VALUES
  (1, 1, 'Segunda', '08:00:00', '12:00:00'),
  (2, 1, 'Quarta', '13:00:00', '17:00:00'),
  (3, 2, 'Terca', '09:00:00', '13:00:00');

INSERT INTO agenda_atendimento (agenda_id, atendimento_id) VALUES
  (1, 1), (1, 2), (2, 1), (3, 1), (3, 3);

INSERT INTO cnn_dupla (id, codigo_cnn, nome) VALUES
  (1, 'CNN-FAKE-001', 'Mamoplastia redutora com lipoaspiracao'),
  (2, 'CNN-FAKE-002', 'Abdominoplastia com consulta de retorno');

INSERT INTO cnn_dupla_procedimento (cnn_dupla_id, procedimento_id) VALUES
  (1, 3), (1, 5),
  (2, 4), (2, 2);

INSERT INTO chatbot_base_setor (id_setor, pergunta, palavras_chave, resposta) VALUES
  (1, 'Qual o horario de funcionamento?', 'horario funcionamento abre fecha', 'A clinica exemplo atende de segunda a sexta, das 8h as 18h.'),
  (2, 'Como solicitar segunda via?', 'boleto pagamento segunda via financeiro', 'Solicite a segunda via pelo canal financeiro ficticio: financeiro@clinica.test.'),
  (3, 'Como remarcar consulta?', 'remarcar consulta agenda', 'Informe nome do paciente, medico e data desejada para remarcacao.');

CREATE VIEW cnn_duplos AS
SELECT id, codigo_cnn AS codigo, nome
FROM cnn_dupla;

CREATE VIEW procedimento_duplo_itens AS
SELECT cnn_dupla_id AS duplo_id, procedimento_id
FROM cnn_dupla_procedimento;
