// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Phần của SentinelRegistry mà cổng này cần dùng.
interface ISentinelRegistry {
    struct AuditReport {
        address target;
        uint64 timestamp;
        uint8 score;
        bytes32 reportHash;
    }

    function latestAudit(address target) external view returns (AuditReport memory);

    function auditCount(address target) external view returns (uint256);
}

/// @title AuditGate - "cổng hải quan" đọc điểm audit ngay trên chain
/// @notice Bất kỳ contract nào cũng có thể hỏi: contract X có đủ an toàn để tương tác không?
///         Cổng chỉ tin dữ liệu trong SentinelRegistry, không tin lời người gọi.
contract AuditGate {
    enum Verdict {
        NotAudited, // chưa từng được audit
        ScoreTooLow, // điểm thấp hơn ngưỡng
        Expired, // audit đã quá cũ
        Safe // đạt
    }

    ISentinelRegistry public immutable registry;
    uint8 public immutable minScore; // điểm tối thiểu để được coi là an toàn
    uint64 public immutable maxAge; // tuổi tối đa của audit (giây), 0 = không giới hạn

    constructor(address _registry, uint8 _minScore, uint64 _maxAge) {
        require(_registry != address(0), "zero registry");
        require(_minScore <= 100, "minScore > 100");
        registry = ISentinelRegistry(_registry);
        minScore = _minScore;
        maxAge = _maxAge;
    }

    /// @notice Trả về kết luận chi tiết, điểm và thời điểm audit mới nhất của `target`.
    function check(address target)
        public
        view
        returns (Verdict verdict, uint8 score, uint64 timestamp)
    {
        // latestAudit() bị revert nếu chưa có audit, nên phải hỏi auditCount() trước.
        if (registry.auditCount(target) == 0) {
            return (Verdict.NotAudited, 0, 0);
        }
        ISentinelRegistry.AuditReport memory r = registry.latestAudit(target);
        if (r.score < minScore) {
            return (Verdict.ScoreTooLow, r.score, r.timestamp);
        }
        if (maxAge != 0 && block.timestamp > uint256(r.timestamp) + maxAge) {
            return (Verdict.Expired, r.score, r.timestamp);
        }
        return (Verdict.Safe, r.score, r.timestamp);
    }

    /// @notice Dạng ngắn gọn cho contract khác gọi: true nếu đủ an toàn.
    function isSafe(address target) external view returns (bool) {
        (Verdict v, , ) = check(target);
        return v == Verdict.Safe;
    }
}

/// @title GuardedLaunchpad - ví dụ một giao thức dùng AuditGate
/// @notice Chỉ cho niêm yết dự án đã được SentinelAgent audit và đạt chuẩn.
contract GuardedLaunchpad {
    AuditGate public immutable gate;
    address[] public listed;

    event Listed(address indexed project, uint8 score);
    error NotSafe(AuditGate.Verdict verdict, uint8 score);

    constructor(AuditGate _gate) {
        gate = _gate;
    }

    function listProject(address project) external {
        (AuditGate.Verdict v, uint8 score, ) = gate.check(project);
        if (v != AuditGate.Verdict.Safe) revert NotSafe(v, score);
        listed.push(project);
        emit Listed(project, score);
    }

    function listedCount() external view returns (uint256) {
        return listed.length;
    }
}
