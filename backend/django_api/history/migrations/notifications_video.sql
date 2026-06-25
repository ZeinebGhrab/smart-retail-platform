-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Hôte : mysql:3306
-- Généré le : jeu. 25 juin 2026 à 18:53
-- Version du serveur : 8.0.40
-- Version de PHP : 8.2.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de données : `shopanalytics`
--

-- --------------------------------------------------------

--
-- Structure de la table `notifications_video`
--

CREATE TABLE `notifications_video` (
  `id` bigint NOT NULL,
  `path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `recording_date` datetime(6) NOT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `send_date` date DEFAULT NULL,
  `create_date` datetime(6) NOT NULL,
  `update_date` datetime(6) NOT NULL,
  `camera_id` bigint NOT NULL,
  `modified_by_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_notified` tinyint(1) NOT NULL,
  `sub_status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `probability` double DEFAULT NULL,
  `metadata` json NOT NULL,
  `detected_by_model` tinyint(1) DEFAULT NULL,
  `nb_alerts` int DEFAULT NULL,
  `assigned_to` varchar(254) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `approval_result` varchar(2) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comment` longtext COLLATE utf8mb4_unicode_ci,
  `modified_by_qualification_id` char(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qualification` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qualification_update_date` datetime(6) DEFAULT NULL,
  `space_id` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Déchargement des données de la table `notifications_video`
--

INSERT INTO `notifications_video` (`id`, `path`, `code`, `recording_date`, `status`, `send_date`, `create_date`, `update_date`, `camera_id`, `modified_by_id`, `send_notified`, `sub_status`, `original_path`, `probability`, `metadata`, `detected_by_model`, `nb_alerts`, `assigned_to`, `approval_result`, `comment`, `modified_by_qualification_id`, `qualification`, `qualification_update_date`, `space_id`) VALUES
(9147470, '/code/media/videos/Chevron_Good_Food_Mart_538_2026-06-05_00-14-53_3lEgpmzN_shoplifting.mp4', 'Camera07_Chevron_Good_20260605-001450651749', '2026-06-05 00:14:53.923255', 'APPROVED', NULL, '2026-06-05 00:14:55.767731', '2026-06-05 00:16:07.677619', 538, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_538_2026-06-05_00-14-53_3lEgpmzN.mp4', 0.5200876, '{\"preds\": [[0.315449059009552, 0.5200875997543335, 0.08386163413524628, 0.06997498124837875, 0.01062672771513462]], \"bboxes\": [[460.0, 159.0, 521.0, 390.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TN', NULL, NULL, NULL, NULL, 1),
(9147539, '/code/media/videos/Supermarket_Maxham_Rd_330_2026-06-05_00-32-03_7GCIWIIH_shoplifting.mp4', 'USA_Juice_20260605-003200012993', '2026-06-05 00:32:03.304079', 'APPROVED', NULL, '2026-06-05 00:32:05.076655', '2026-06-05 00:32:31.530266', 330, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Supermarket_Maxham_Rd_330_2026-06-05_00-32-03_7GCIWIIH.mp4', 0.55588734, '{\"preds\": [[0.029924888163805008, 0.5558873414993286, 0.08392642438411713, 0.16658197343349457, 0.1636793464422226]], \"bboxes\": [[506.0, 75.0, 608.0, 476.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148023, '/code/media/videos/Thornton_Food_Mart_528_2026-06-05_01-50-44_3gVTtt80_shoplifting.mp4', 'Front_Thornton_20260605-015041252856', '2026-06-05 01:50:44.624935', 'APPROVED', NULL, '2026-06-05 01:50:46.522394', '2026-06-05 01:51:09.880158', 528, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Thornton_Food_Mart_528_2026-06-05_01-50-44_3gVTtt80.mp4', 0.4892452, '{\"preds\": [[0.48924520611763, 0.1744457483291626, 0.22841063141822815, 0.08979698270559311, 0.018101388588547707]], \"bboxes\": [[334.0, 189.0, 429.0, 450.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148024, '/code/media/videos/Thornton_Food_Mart_526_2026-06-05_01-50-48_FqNyCeVx_fausse_alert_shoplifting.mp4', 'Outside_Registre_Thornton_20260605-015045318672', '2026-06-05 01:50:48.709492', 'APPROVED', NULL, '2026-06-05 01:50:50.680255', '2026-06-05 01:51:24.919747', 526, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Thornton_Food_Mart_526_2026-06-05_01-50-48_FqNyCeVx.mp4', 0.55344963, '{\"preds\": [[0.5534496307373047, 0.1364257037639618, 0.25939661264419556, 0.008876064792275429, 0.04185199365019798]], \"bboxes\": [[290.0, 213.0, 381.0, 465.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148028, '/code/media/videos/Thornton_Food_Mart_526_2026-06-05_01-51-10_kf1Y-Wev_shoplifting.mp4', 'Outside_Registre_Thornton_20260605-015107408640', '2026-06-05 01:51:10.752677', 'APPROVED', NULL, '2026-06-05 01:51:12.664739', '2026-06-05 01:51:53.874122', 526, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Thornton_Food_Mart_526_2026-06-05_01-51-10_kf1Y-Wev.mp4', 0.5323726, '{\"preds\": [[0.5323725938796997, 0.08268506079912186, 0.3491384983062744, 0.010709097608923912, 0.025094687938690186]], \"bboxes\": [[302.0, 205.0, 387.0, 466.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148029, '/code/media/videos/Thornton_Food_Mart_526_2026-06-05_01-51-29_lWXfz3a5_shoplifting.mp4', 'Outside_Registre_Thornton_20260605-015126614923', '2026-06-05 01:51:29.994630', 'APPROVED', NULL, '2026-06-05 01:51:31.904650', '2026-06-05 01:52:03.967574', 526, '0cd9844303c642b28d3f9ec136956ac1', 0, 'DEFAULTE', 'Thornton_Food_Mart_526_2026-06-05_01-51-29_lWXfz3a5.mp4', 0.40067026, '{\"preds\": [[0.40067026019096375, 0.19680261611938477, 0.32447266578674316, 0.012005036696791649, 0.0660495012998581]], \"bboxes\": [[297.0, 192.0, 378.0, 446.0]], \"number_of_persons\": 1}', NULL, NULL, 'Sendra_Rabenarivo@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148310, '/code/media/videos/Chevron_Good_Food_Mart_439_2026-06-05_03-07-31_hWriVRRm_shoplifting.mp4', 'Camera03_Chevron_Good_20260605-030727787669', '2026-06-05 03:07:31.108269', 'APPROVED', NULL, '2026-06-05 03:07:32.928154', '2026-06-05 03:07:59.082402', 439, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_439_2026-06-05_03-07-31_hWriVRRm.mp4', 0.43488708, '{\"preds\": [[0.08732332289218903, 0.4348870813846588, 0.19185252487659457, 0.10269126296043396, 0.18324582278728485]], \"bboxes\": [[494.0, 64.0, 536.0, 237.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148329, '/code/media/videos/Supermarket_Maxham_Rd_330_2026-06-05_03-16-03_1XXhfnZH_shoplifting.mp4', 'USA_Juice_20260605-031600348379', '2026-06-05 03:16:03.707078', 'APPROVED', NULL, '2026-06-05 03:16:05.536432', '2026-06-05 03:16:30.009677', 330, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Supermarket_Maxham_Rd_330_2026-06-05_03-16-03_1XXhfnZH.mp4', 0.4168128, '{\"preds\": [[0.0993892028927803, 0.41681280732154846, 0.14876438677310944, 0.08468065410852432, 0.2503528892993927]], \"bboxes\": [[475.0, 214.0, 544.0, 463.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148359, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_03-20-41_DbLQZbwv_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-032037785342', '2026-06-05 03:20:41.202982', 'APPROVED', NULL, '2026-06-05 03:20:43.021483', '2026-06-05 03:21:03.683890', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_03-20-41_DbLQZbwv.mp4', 0.54534733, '{\"preds\": [[0.10448872298002244, 0.5453473329544067, 0.08561499416828156, 0.10048583894968031, 0.16406308114528656]], \"bboxes\": [[352.0, 165.0, 434.0, 524.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148361, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_03-21-23_RADBAI8u_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-032120650834', '2026-06-05 03:21:23.915099', 'APPROVED', NULL, '2026-06-05 03:21:25.759286', '2026-06-05 03:21:38.607994', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_03-21-23_RADBAI8u.mp4', 0.47959507, '{\"preds\": [[0.4795950651168823, 0.47215962409973145, 0.02612220868468285, 0.005583507474511862, 0.016539551317691803]], \"bboxes\": [[357.0, 147.0, 440.0, 475.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148365, '/code/media/videos/Chevron_Good_Food_Mart_439_2026-06-05_03-22-20_a5QBf573_shoplifting.mp4', 'Camera03_Chevron_Good_20260605-032217379090', '2026-06-05 03:22:20.589358', 'APPROVED', NULL, '2026-06-05 03:22:22.499727', '2026-06-05 03:22:36.380492', 439, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_439_2026-06-05_03-22-20_a5QBf573.mp4', 0.6032253, '{\"preds\": [[0.15386565029621124, 0.6032252907752991, 0.05699228122830391, 0.0650872215628624, 0.1208295077085495], [0.01787513494491577, 0.005451608914881945, 0.28180718421936035, 0.4719382524490357, 0.22292783856391907], [0.011790622025728226, 0.0019398621516302228, 0.29704001545906067, 0.5132391452789307, 0.17599041759967804]], \"bboxes\": [[317.0, 207.0, 399.0, 486.0], [178.0, 89.0, 267.0, 462.0], [186.0, 50.0, 258.0, 287.0]], \"number_of_persons\": 3}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148378, '/code/media/videos/Supermarket_Maxham_Rd_325_2026-06-05_03-29-12_T5IXLi2E_shoplifting.mp4', 'USA_Aisle_20260605-032908947729', '2026-06-05 03:29:12.166388', 'APPROVED', NULL, '2026-06-05 03:29:14.067788', '2026-06-05 03:29:30.823601', 325, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Supermarket_Maxham_Rd_325_2026-06-05_03-29-12_T5IXLi2E.mp4', 0.36179096, '{\"preds\": [[0.1982450634241104, 0.3617909550666809, 0.15375395119190216, 0.20735366642475128, 0.0788564383983612], [0.0037539161276072264, 0.011562876403331757, 0.1547095775604248, 0.4840434193611145, 0.3459302484989166]], \"bboxes\": [[259.0, 49.0, 349.0, 351.0], [343.0, 54.0, 405.0, 241.0]], \"number_of_persons\": 2}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148396, '/code/media/videos/Supermarket_Maxham_Rd_325_2026-06-05_03-39-01_no2gZ1Bk_shoplifting.mp4', 'USA_Aisle_20260605-033857801613', '2026-06-05 03:39:01.085327', 'APPROVED', NULL, '2026-06-05 03:39:02.977064', '2026-06-05 03:39:36.708227', 325, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Supermarket_Maxham_Rd_325_2026-06-05_03-39-01_no2gZ1Bk.mp4', 0.45301753, '{\"preds\": [[0.09664156287908554, 0.45301753282547, 0.1918196678161621, 0.21736018359661105, 0.04116109013557434]], \"bboxes\": [[290.0, 77.0, 373.0, 394.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148401, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_03-40-00_ptJHCheb_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-033957529018', '2026-06-05 03:40:00.962393', 'APPROVED', NULL, '2026-06-05 03:40:02.774074', '2026-06-05 03:40:17.743686', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_03-40-00_ptJHCheb.mp4', 0.46620616, '{\"preds\": [[0.05417850241065025, 0.4662061631679535, 0.10321512073278429, 0.03797072917222977, 0.33842942118644714]], \"bboxes\": [[316.0, 177.0, 371.0, 480.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148411, '/code/media/videos/Supermarket_Maxham_Rd_325_2026-06-05_03-42-45_vsCb1TM5_shoplifting.mp4', 'USA_Aisle_20260605-034242570180', '2026-06-05 03:42:45.765030', 'APPROVED', NULL, '2026-06-05 03:42:47.797048', '2026-06-05 03:43:17.315817', 325, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Supermarket_Maxham_Rd_325_2026-06-05_03-42-45_vsCb1TM5.mp4', 0.6853896, '{\"preds\": [[0.6853895783424377, 0.1830345243215561, 0.10490280389785768, 0.024386988952755928, 0.002286134520545602], [0.1737181842327118, 0.118784099817276, 0.264049232006073, 0.33054572343826294, 0.1129026934504509]], \"bboxes\": [[271.0, 72.0, 358.0, 434.0], [351.0, 38.0, 407.0, 229.0]], \"number_of_persons\": 2}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148423, '/code/media/videos/Chevron_Good_Food_Mart_537_2026-06-05_03-47-37_OOj9HC3F_shoplifting.mp4', 'Camera06_Chevron_Good_20260605-034734072441', '2026-06-05 03:47:37.316518', 'APPROVED', NULL, '2026-06-05 03:47:39.113493', '2026-06-05 03:47:57.967690', 537, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_537_2026-06-05_03-47-37_OOj9HC3F.mp4', 0.40041724, '{\"preds\": [[0.4004172384738922, 0.10568635165691376, 0.3411597013473511, 0.08813195675611496, 0.06460478156805038], [0.007272005081176758, 0.007801722269505262, 0.22446495294570923, 0.2815420925617218, 0.47891926765441895]], \"bboxes\": [[450.0, 108.0, 494.0, 335.0], [335.0, 126.0, 385.0, 257.0]], \"number_of_persons\": 2}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0),
(9148479, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_04-07-09_uX8Hb5LI_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-040705762557', '2026-06-05 04:07:09.251054', 'APPROVED', NULL, '2026-06-05 04:07:11.190756', '2026-06-05 04:07:26.371445', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_04-07-09_uX8Hb5LI.mp4', 0.38400084, '{\"preds\": [[0.38400083780288696, 0.02654309570789337, 0.3469158411026001, 0.22929736971855164, 0.013242841698229311]], \"bboxes\": [[337.0, 157.0, 449.0, 514.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148509, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_04-28-43_mcbyjpOf_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-042840010074', '2026-06-05 04:28:43.384359', 'APPROVED', NULL, '2026-06-05 04:28:45.375583', '2026-06-05 04:28:59.218583', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_04-28-43_mcbyjpOf.mp4', 0.5654155, '{\"preds\": [[0.5654155015945435, 0.033364176750183105, 0.37664794921875, 0.013719399459660052, 0.010852937586605549]], \"bboxes\": [[335.0, 230.0, 424.0, 477.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148511, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_04-31-10_wqEWrmMx_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-043107089954', '2026-06-05 04:31:10.395132', 'APPROVED', NULL, '2026-06-05 04:31:12.251333', '2026-06-05 04:31:28.477752', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_04-31-10_wqEWrmMx.mp4', 0.7385698, '{\"preds\": [[0.1227063164114952, 0.7385697960853577, 0.03808695450425148, 0.01451275870203972, 0.08612414449453354]], \"bboxes\": [[340.0, 177.0, 422.0, 486.0]], \"number_of_persons\": 1}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TN', NULL, NULL, NULL, NULL, 0),
(9148515, '/code/media/videos/Chevron_Good_Food_Mart_437_2026-06-05_04-35-58_qBU9WejZ_shoplifting.mp4', 'Camera01_Chevron_Good_20260605-043555280248', '2026-06-05 04:35:58.764020', 'APPROVED', NULL, '2026-06-05 04:36:00.745756', '2026-06-05 04:36:13.697492', 437, '7bff35c9b58948fd856b05a20a8b9f85', 0, 'DEFAULTE', 'Chevron_Good_Food_Mart_437_2026-06-05_04-35-58_qBU9WejZ.mp4', 0.42235947, '{\"preds\": [[0.056494198739528656, 0.4223594665527344, 0.30540478229522705, 0.06351813673973083, 0.1522233635187149], [0.07103465497493744, 0.07229434698820114, 0.5248790383338928, 0.29100021719932556, 0.040791768580675125]], \"bboxes\": [[220.0, 123.0, 287.0, 385.0], [347.0, 134.0, 436.0, 438.0]], \"number_of_persons\": 2}', NULL, NULL, 'Andrianina_Yannick@gmail.com', 'TP', NULL, NULL, NULL, NULL, 0);

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `notifications_video`
--
ALTER TABLE `notifications_video`
  ADD PRIMARY KEY (`id`),
  ADD KEY `notificatio_create__0a3f0f_idx` (`create_date`,`send_date`,`code`),
  ADD KEY `notifications_video_camera_id_ab73fe08_fk_notificat` (`camera_id`),
  ADD KEY `notifications_video_modified_by_id_388ac190_fk_users_user_id` (`modified_by_id`),
  ADD KEY `notificatio_camera__0e4e20_idx` (`camera_id`,`status`),
  ADD KEY `notificatio_recordi_93ac7c_idx` (`recording_date`),
  ADD KEY `notificatio_status_629629_idx` (`status`,`sub_status`),
  ADD KEY `notificatio_probabi_26e203_idx` (`probability`),
  ADD KEY `notificatio_modifie_088957_idx` (`modified_by_id`,`status`,`update_date`),
  ADD KEY `notifications_video_modified_by_qualific_0a705b48_fk_users_use` (`modified_by_qualification_id`);

--
-- AUTO_INCREMENT pour les tables déchargées
--

--
-- AUTO_INCREMENT pour la table `notifications_video`
--
ALTER TABLE `notifications_video`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10031670;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
