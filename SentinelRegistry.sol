// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SentinelRegistry - sổ cái lưu kết quả audit do AI Agent cấp
/// @notice Chỉ địa chỉ "agent" (ví của backend) mới được ghi báo cáo.
contract SentinelRegistry {
    struct AuditReport {
        address target;      // contract được audit
        uint64 timestamp;    // thời điểm audit
        uint8 score;         // 0..100
        bytes32 reportHash;  // keccak256 của báo cáo JSON (lưu off-chain)
    }

    address public owner;
    address public agent;

    // target => danh sách các lần audit (giữ lịch sử, không ghi đè)
    mapping(address => AuditReport[]) private reports;

    event AuditRecorded(
        address indexed target,
        uint8 score,
        bytes32 reportHash,
        uint256 index
    );
    event AgentChanged(address indexed newAgent);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyAgent() {
        require(msg.sender == agent, "not agent");
        _;
    }

    constructor(address _agent) {
        owner = msg.sender;
        agent = _agent;
    }

    function setAgent(address _agent) external onlyOwner {
        agent = _agent;
        emit AgentChanged(_agent);
    }

    /// @notice Agent gọi hàm này để "đóng dấu" kết quả audit
    function recordAudit(
        address target,
        uint8 score,
        bytes32 reportHash
    ) external onlyAgent {
        require(score <= 100, "score > 100");
        reports[target].push(
            AuditReport(target, uint64(block.timestamp), score, reportHash)
        );
        emit AuditRecorded(target, score, reportHash, reports[target].length - 1);
    }

    /// @notice Lấy audit mới nhất của một contract
    function latestAudit(address target)
        external
        view
        returns (AuditReport memory)
    {
        uint256 n = reports[target].length;
        require(n > 0, "no audit");
        return reports[target][n - 1];
    }

    function auditCount(address target) external view returns (uint256) {
        return reports[target].length;
    }
}
